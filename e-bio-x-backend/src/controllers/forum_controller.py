import os
import re
import uuid
from datetime import datetime
from flask import request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.config.database import db
from src.models.user import User
from src.models.course import Course
from src.models.material import Material
from src.models.material_section import MaterialSection
from src.models.enrollment import Enrollment
from src.models.forum import (
    Forum, ForumMember, ForumPost, ForumReaction, ForumMention,
    ForumAttachment, ForumQuestion, ForumAnswer, ForumFeedback,
    ForumReport, ForumModerationLog, Notification, ForumSetting,
)
from src.services import forum_service as fs

FORUM_TYPES = ('GENERAL_DISCUSSION', 'PRESENTATION', 'QUESTION_ANSWER', 'CASE_STUDY')
FORUM_VISIBILITY = ('PRIVATE', 'CLASS', 'COURSE')
FORUM_STATUS = ('DRAFT', 'SCHEDULED', 'ACTIVE', 'CLOSED', 'ARCHIVED')
REACTION_TYPES = ('like', 'idea', 'love', 'confused', 'insight', 'agree', 'disagree')
REPORT_REASONS = ('SPAM', 'INAPPROPRIATE', 'OFF_TOPIC', 'MISINFORMATION', 'OTHER')
ALLOWED_ATTACHMENT_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'pdf', 'docx', 'pptx', 'mp4'}
MAX_ATTACHMENT_SIZE = 40 * 1024 * 1024

_MENTION_RE = re.compile(r'@([A-Za-z0-9_.\-]+)')

IMG_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif'}


def _current_user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _attachment_folder():
    folder = current_app.config.get('UPLOAD_FOLDER')
    if not folder:
        folder = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'uploads')
    return folder


def _matches_signature(file, ext):
    """Magic-byte check reused from material upload validation."""
    try:
        head = file.read(16)
        file.seek(0)
    except Exception:
        return False
    if not head:
        return False
    if ext == 'pdf':
        return head.startswith(b'%PDF')
    if ext == 'png':
        return head.startswith(b'\x89PNG\r\n\x1a\n')
    if ext in ('jpg', 'jpeg'):
        return head.startswith(b'\xff\xd8\xff')
    if ext == 'webp':
        return head.startswith(b'RIFF') and head[8:12] == b'WEBP'
    if ext == 'gif':
        return head.startswith(b'GIF8')
    if ext == 'mp4':
        return len(head) >= 12 and head[4:8] == b'ftyp'
    # docx/pptx are zip archives
    if ext in ('docx', 'pptx'):
        return head.startswith(b'PK\x03\x04')
    return False


def _save_attachment(file):
    original = file.filename or 'file'
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
    if ext not in ALLOWED_ATTACHMENT_EXT:
        return None, 'Tipe file tidak diizinkan'
    if not _matches_signature(file, ext):
        return None, 'Konten file tidak sesuai dengan tipe yang diizinkan'
    try:
        file.seek(0)
        folder = _attachment_folder()
        os.makedirs(folder, exist_ok=True)
        name = f"{uuid.uuid4().hex}_{original}"
        path = os.path.join(folder, name)
        file.save(path)
        size = os.path.getsize(path)
    except Exception:
        return None, 'Gagal menyimpan file'
    return {
        'name': name,
        'path': path,
        'url': f'/uploads/{name}',
        'size': size,
        'type': ext,
        'original': original,
    }, None


def _is_meaningful(content):
    if content is None:
        return False
    c = fs.sanitize_text(content)
    stripped = c.lower().strip()
    if len(stripped) < 15:
        return False
    if stripped in fs.SPAM_SHORT:
        return False
    return True


def _extract_and_create_mentions(post, forum):
    """Parse @usernames from post content and create mention rows + notifications."""
    tokens = set(_MENTION_RE.findall(post.content or ''))
    if not tokens:
        return
    course_members = _course_member_ids(forum)
    for token in tokens:
        member = User.query.filter(db.func.lower(User.name) == token.lower()).first()
        if not member:
            continue
        if member.id not in course_members:
            continue
        if member.id == post.author_id:
            continue
        existing = ForumMention.query.filter_by(post_id=post.id, mentioned_user_id=member.id).first()
        if existing:
            continue
        db.session.add(ForumMention(post_id=post.id, mentioned_user_id=member.id))
        fs.notify(
            member.id, post.author_id, 'mention',
            f'{post.author.name} menyebut Anda dalam diskusi "{post.forum.title}".',
            forum_id=post.forum_id, post_id=post.id,
        )


def _course_member_ids(forum):
    ids = set()
    if forum.course_id:
        enrollments = Enrollment.query.filter_by(course_id=forum.course_id).all()
        ids.update(e.student_id for e in enrollments)
        if forum.course:
            ids.add(forum.course.teacher_id)
    if forum.material_id and forum.material and forum.material.teacher_id:
        ids.add(forum.material.teacher_id)
    ids.add(forum.created_by)
    if forum.presenter_id:
        ids.add(forum.presenter_id)
    for m in forum.members:
        ids.add(m.user_id)
    return ids


def _visible_forums(user):
    forums = Forum.query.order_by(Forum.is_pinned.desc(), Forum.created_at.desc()).all()
    result = []
    for f in forums:
        fs.resolve_forum_status(f)
        if not fs.can_view_forum(f, user):
            continue
        result.append(f)
    return result


def _forum_has_replies(forum):
    return ForumPost.query.filter(ForumPost.forum_id == forum.id, ForumPost.parent_id.isnot(None)).first() is not None


# ============================================================
# LIST / CREATE / DETAIL / UPDATE / DELETE
# ============================================================

@jwt_required()
def list_forums():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    forum_type = request.args.get('type')
    topic = request.args.get('topic')
    status = request.args.get('status')
    q = (request.args.get('q') or '').strip().lower()
    sort = request.args.get('sort', 'latest')
    course_id = request.args.get('course_id', type=int)
    material_id = request.args.get('material_id', type=int)
    scope = request.args.get('scope')  # 'my'

    forums = _visible_forums(user)
    filtered = []
    for f in forums:
        if forum_type and f.type != forum_type:
            continue
        if topic and (f.topic or '').lower() != topic.lower():
            continue
        if status and f.status != status:
            continue
        if course_id and f.course_id != course_id:
            continue
        if material_id and f.material_id != material_id:
            continue
        if scope == 'my' and str(f.created_by) != str(user.id):
            continue
        if q:
            hay = ' '.join([f.title, f.description or '', f.topic or '',
                            ' '.join((f.tags or '').split(',')),
                            f.creator.name if f.creator else '',
                            f.presentation_group_name or '',
                            f.presenter.name if f.presenter else ''])
            if q not in hay.lower():
                continue
        filtered.append(f)

    if sort == 'replies':
        filtered.sort(key=lambda f: len([p for p in f.posts if p.parent_id is not None]), reverse=True)
    elif sort == 'reactions':
        filtered.sort(key=lambda f: sum(len(p.reactions) for p in f.posts), reverse=True)
    elif sort == 'unanswered':
        filtered.sort(key=lambda f: len([q for q in f.questions if q.status == 'UNANSWERED']), reverse=True)
    else:
        filtered.sort(key=lambda f: (f.is_pinned, f.created_at), reverse=True)

    recommended = []
    if user.role == 'student':
        recommended = _recommended_forums(user, filtered)

    return jsonify({
        'forums': [fs.forum_payload(f, user) for f in filtered],
        'recommended': [fs.forum_payload(f, user) for f in recommended],
        'topics': sorted({f.topic for f in _visible_forums(user) if f.topic}),
    }), 200


def _recommended_forums(user, visible):
    """Lightweight fallback recommendation: same topic as the student's weakest material."""
    try:
        from src.ml.feature_service import build_student_features
        weakest = None
        if visible:
            return visible[:3]
    except Exception:
        return visible[:3]
    return visible[:3]


@jwt_required()
def create_forum():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin', 'student'):
        return jsonify({'error': 'Akses ditolak'}), 403

    if user.role == 'student' and not fs.allow_student_creation():
        return jsonify({'error': 'Siswa tidak diizinkan membuat forum saat ini'}), 403

    if request.is_json:
        return _create_forum_json(user)
    return _create_forum_form(user)


def _parse_forum_payload(data, user):
    forum_type = data.get('type') or 'GENERAL_DISCUSSION'
    if forum_type not in FORUM_TYPES:
        return None, 'Tipe forum tidak valid'
    title = fs.sanitize_text(data.get('title') or '')
    if not title:
        return None, 'Judul forum wajib diisi'

    course_id = data.get('course_id')
    if course_id is not None:
        try:
            course_id = int(course_id)
        except (TypeError, ValueError):
            return None, 'course_id tidak valid'
    course = None
    if course_id:
        course = Course.query.get(course_id)
        if not course:
            return None, 'Kelas tidak ditemukan'
        if user.role == 'student':
            enrolled = Enrollment.query.filter_by(student_id=user.id, course_id=course_id).first()
            if not enrolled:
                return None, 'Anda harus bergabung ke kelas sebelum membuat forum'

    material_id = data.get('material_id')
    if material_id is not None:
        try:
            material_id = int(material_id)
        except (TypeError, ValueError):
            material_id = None

    lesson_id = data.get('lesson_id')
    if lesson_id is not None:
        try:
            lesson_id = int(lesson_id)
        except (TypeError, ValueError):
            lesson_id = None

    visibility = data.get('visibility') or ('CLASS' if user.role == 'student' else 'COURSE')
    if visibility not in FORUM_VISIBILITY:
        return None, 'Visibility tidak valid'

    status = data.get('status') or 'DRAFT'
    if status not in FORUM_STATUS:
        return None, 'Status tidak valid'

    forum = Forum(
        type=forum_type,
        title=title,
        description=fs.sanitize_text(data.get('description') or ''),
        topic=fs.sanitize_text(data.get('topic') or ''),
        category=fs.sanitize_text(data.get('category') or ''),
        tags=fs.sanitize_text(data.get('tags') or ''),
        pinned_question=fs.sanitize_text(data.get('pinned_question') or ''),
        course_id=course_id,
        material_id=material_id,
        lesson_id=lesson_id,
        created_by=user.id,
        visibility=visibility,
        status=status,
        start_at=_parse_dt(data.get('start_at')),
        end_at=_parse_dt(data.get('end_at')),
        is_pinned=bool(data.get('is_pinned', False)) if user.role in ('teacher', 'admin') else False,
        presentation_group_name=fs.sanitize_text(data.get('presentation_group_name') or ''),
        presenter_id=int(data['presenter_id']) if data.get('presenter_id') else None,
        presentation_file_url=data.get('presentation_file_url'),
        presentation_file_name=data.get('presentation_file_name'),
        presentation_video_url=data.get('presentation_video_url'),
        presentation_video_name=data.get('presentation_video_name'),
        presenter_question_enabled=bool(data.get('presenter_question_enabled', True)),
    )
    return forum, None


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00').replace('T', ' ').split('+')[0])
    except Exception:
        return None


def _create_forum_json(user):
    data = request.get_json(silent=True) or {}
    forum, err = _parse_forum_payload(data, user)
    if err:
        return jsonify({'error': err}), 400
    db.session.add(forum)
    db.session.flush()
    _apply_members(forum, data, user)
    db.session.commit()

    fs.notify_maybe = None
    _award_after_forum(user, forum)
    fs.log_forum_event(user, forum, 'FORUM_CREATED', {'forum_id': forum.id})
    return jsonify({'message': 'Forum berhasil dibuat', 'forum': fs.forum_payload(forum, user)}), 201


def _apply_members(forum, data, user):
    member_ids = set()
    if forum.presenter_id:
        member_ids.add(forum.presenter_id)
    raw = data.get('member_ids') or data.get('presenters')
    if isinstance(raw, list):
        for mid in raw:
            try:
                member_ids.add(int(mid))
            except (TypeError, ValueError):
                pass
    if user.role == 'student':
        member_ids.add(user.id)
    for mid in member_ids:
        if ForumMember.query.filter_by(forum_id=forum.id, user_id=mid).first():
            continue
        role = 'presenter' if (forum.type == 'PRESENTATION' and (mid == forum.presenter_id or mid in member_ids)) else 'member'
        db.session.add(ForumMember(forum_id=forum.id, user_id=mid, role=role))


def _create_forum_form(user):
    data = request.form.to_dict()
    data['member_ids'] = _parse_csv_ids(request.form.get('member_ids'))
    forum, err = _parse_forum_payload(data, user)
    if err:
        return jsonify({'error': err}), 400

    db.session.add(forum)
    db.session.flush()

    file = request.files.get('presentation_file')
    if file and file.filename:
        saved, err = _save_attachment(file)
        if err:
            db.session.rollback()
            return jsonify({'error': err}), 400
        forum.presentation_file_url = saved['url']
        forum.presentation_file_name = saved['original']
    video = request.files.get('presentation_video')
    if video and video.filename:
        saved, err = _save_attachment(video)
        if err:
            db.session.rollback()
            return jsonify({'error': err}), 400
        forum.presentation_video_url = saved['url']
        forum.presentation_video_name = saved['original']

    _apply_members(forum, data, user)
    db.session.commit()

    fs.log_forum_event(user, forum, 'FORUM_CREATED', {'forum_id': forum.id})
    _award_after_forum(user, forum)
    return jsonify({'message': 'Forum berhasil dibuat', 'forum': fs.forum_payload(forum, user)}), 201


def _parse_csv_ids(value):
    if not value:
        return []
    return [int(x) for x in str(value).split(',') if x.strip().isdigit()]


def _award_after_forum(user, forum):
    if forum.status != 'DRAFT':
        fs.award_xp(user.id, 'forum_created', 20, 'forum', forum.id)
        fs.evaluate_achievements(user.id)


@jwt_required()
def get_forum_detail(forum_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    forum = Forum.query.get(forum_id)
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    fs.resolve_forum_status(forum)
    if not fs.can_view_forum(forum, user):
        return jsonify({'error': 'Anda tidak memiliki akses ke forum ini'}), 403
    if forum.status == 'DRAFT' and not fs.can_manage_forum(forum, user):
        return jsonify({'error': 'Forum draft hanya dapat dilihat oleh pembuatnya'}), 403

    # lazy record view + learning event
    if user.role == 'student' and forum.status in ('ACTIVE', 'CLOSED'):
        fs.log_forum_event(user, forum, 'FORUM_VIEWED', {'forum_id': forum.id})

    page = request.args.get('page', 1, type=int)
    per_page = min(request.args.get('per_page', 20, type=int), 50)

    root_posts = ForumPost.query.filter_by(
        forum_id=forum.id, parent_id=None
    ).filter(ForumPost.deleted_at.is_(None)).order_by(
        ForumPost.is_pinned.desc(), ForumPost.created_at.asc()
    ).offset((page - 1) * per_page).limit(per_page).all()

    payload = fs.forum_payload(forum, user)
    payload['posts'] = [fs.post_payload(p, user, include_replies=True) for p in root_posts]
    payload['page'] = page
    payload['per_page'] = per_page
    payload['total_root_posts'] = ForumPost.query.filter_by(
        forum_id=forum.id, parent_id=None
    ).filter(ForumPost.deleted_at.is_(None)).count()

    # presenter dashboard data
    if forum.type == 'PRESENTATION':
        qs = ForumQuestion.query.filter_by(forum_id=forum.id).all()
        payload['presentation'] = {
            'questions': len(qs),
            'answered': sum(1 for q in qs if q.status == 'ANSWERED'),
            'unanswered': sum(1 for q in qs if q.status == 'UNANSWERED'),
        }

    return jsonify(payload), 200


@jwt_required()
def update_forum(forum_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    forum = Forum.query.get(forum_id)
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    if not fs.can_manage_forum(forum, user):
        return jsonify({'error': 'Anda tidak berhak mengubah forum ini'}), 403

    data = request.get_json(silent=True) or {}
    editable = ['title', 'description', 'topic', 'category', 'tags', 'pinned_question',
                'visibility', 'start_at', 'end_at', 'presentation_group_name',
                'presentation_file_url', 'presentation_file_name',
                'presentation_video_url', 'presentation_video_name',
                'presenter_question_enabled']
    for field in editable:
        if field in data:
            if field in ('start_at', 'end_at'):
                setattr(forum, field, _parse_dt(data[field]))
            elif field == 'presenter_question_enabled':
                setattr(forum, field, bool(data[field]))
            else:
                setattr(forum, field, fs.sanitize_text(data[field] or ''))
    if 'presenter_id' in data and data['presenter_id']:
        forum.presenter_id = int(data['presenter_id'])
    if 'status' in data and data['status'] in FORUM_STATUS:
        forum.status = data['status']
    if 'type' in data and data['type'] in FORUM_TYPES:
        forum.type = data['type']
    if 'member_ids' in data and isinstance(data['member_ids'], list):
        existing = {m.user_id for m in forum.members}
        for mid in data['member_ids']:
            if mid not in existing:
                db.session.add(ForumMember(forum_id=forum.id, user_id=int(mid), role='presenter' if forum.type == 'PRESENTATION' else 'member'))
    forum.updated_at = datetime.utcnow()
    db.session.commit()
    _award_after_forum(user, forum)
    return jsonify({'message': 'Forum berhasil diperbarui', 'forum': fs.forum_payload(forum, user)}), 200


def _purge_forum_dependents(forum):
    """Delete rows that reference forum posts via FKs (no cascade in MySQL)."""
    post_ids = [p.id for p in forum.posts]
    if post_ids:
        Notification.query.filter(Notification.post_id.in_(post_ids)).delete(synchronize_session=False)
        ForumReport.query.filter(ForumReport.post_id.in_(post_ids)).delete(synchronize_session=False)
        ForumFeedback.query.filter(ForumFeedback.post_id.in_(post_ids)).delete(synchronize_session=False)
        ForumMention.query.filter(ForumMention.post_id.in_(post_ids)).delete(synchronize_session=False)
        ForumReaction.query.filter(ForumReaction.post_id.in_(post_ids)).delete(synchronize_session=False)
        ForumAnswer.query.filter(ForumAnswer.answer_post_id.in_(post_ids)).delete(synchronize_session=False)
        ForumModerationLog.query.filter(ForumModerationLog.post_id.in_(post_ids)).delete(synchronize_session=False)
    ForumQuestion.query.filter(ForumQuestion.forum_id == forum.id).delete(synchronize_session=False)
    Notification.query.filter(Notification.forum_id == forum.id).delete(synchronize_session=False)
    ForumModerationLog.query.filter(ForumModerationLog.forum_id == forum.id).delete(synchronize_session=False)


def _purge_post_dependents(post):
    Notification.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    ForumReport.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    ForumFeedback.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    ForumMention.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    ForumReaction.query.filter_by(post_id=post.id).delete(synchronize_session=False)
    ForumAnswer.query.filter_by(answer_post_id=post.id).delete(synchronize_session=False)
    ForumModerationLog.query.filter_by(post_id=post.id).delete(synchronize_session=False)


@jwt_required()
def delete_forum(forum_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    forum = Forum.query.get(forum_id)
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    if not fs.can_manage_forum(forum, user):
        return jsonify({'error': 'Anda tidak berhak menghapus forum ini'}), 403

    disk = [forum.presentation_file_url, forum.presentation_video_url]
    attachments = ForumAttachment.query.filter_by(forum_id=forum.id).all()
    disk += [a.file_url for a in attachments]
    _purge_forum_dependents(forum)
    db.session.delete(forum)
    db.session.commit()
    folder = _attachment_folder()
    for url in disk:
        if not url:
            continue
        name = os.path.basename(url)
        path = os.path.join(folder, name)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
    return jsonify({'message': 'Forum berhasil dihapus'}), 200


# ============================================================
# POSTS & REPLIES
# ============================================================

@jwt_required()
def create_post(forum_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    forum = Forum.query.get(forum_id)
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    fs.resolve_forum_status(forum)
    if not fs.can_post_in_forum(forum, user):
        return jsonify({'error': 'Forum terkunci atau tidak menerima diskusi baru'}), 403

    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    if not fs.check_idempotency(user.id, request_id):
        return jsonify({'error': 'Permintaan duplikat terdeteksi'}), 400
    if not fs.check_rate_limit(user.id):
        return jsonify({'error': 'Anda terlalu cepat mengirim diskusi. Silakan tunggu beberapa saat.'}), 429

    content = fs.plain_links(fs.sanitize_text(data.get('content') or ''))
    if not content:
        return jsonify({'error': 'Isi posting wajib diisi'}), 400
    post_type = data.get('post_type')
    if post_type not in ('post', 'question'):
        post_type = 'post'

    post = ForumPost(
        forum_id=forum.id,
        author_id=user.id,
        parent_id=None,
        content=content,
        post_type=post_type,
        quoted_post_id=int(data['quoted_post_id']) if data.get('quoted_post_id') else None,
    )
    db.session.add(post)
    db.session.flush()

    attachment_ids = data.get('attachment_ids') or []
    _link_attachments(post, attachment_ids, user.id)

    if post_type == 'question' and forum.type == 'PRESENTATION':
        presenter_id = int(data['presenter_id']) if data.get('presenter_id') else (forum.presenter_id or None)
        db.session.add(ForumQuestion(
            forum_id=forum.id, post_id=post.id, questioner_id=user.id, presenter_id=presenter_id,
        ))

    _extract_and_create_mentions(post, forum)
    db.session.commit()

    event = 'QUESTION_CREATED' if post_type == 'question' else 'POST_CREATED'
    fs.log_forum_event(user, forum, event, {'post_id': post.id})
    if post_type == 'question':
        fs.award_xp(user.id, 'question_created', 5, 'post', post.id)
        if forum.type == 'PRESENTATION' and forum.presenter_id:
            fs.notify(forum.presenter_id, user.id, 'presenter_question',
                      f'{user.name} mengajukan pertanyaan di "{forum.title}".',
                      forum_id=forum.id, post_id=post.id)
    elif _is_meaningful(content):
        fs.award_xp(user.id, 'post_created', 10, 'post', post.id)
    fs.evaluate_achievements(user.id)

    return jsonify({'message': 'Posting berhasil dikirim', 'post': fs.post_payload(post, user)}), 201


@jwt_required()
def create_reply(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    parent = ForumPost.query.get(post_id)
    if not parent or parent.deleted_at is not None:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404
    forum = parent.forum
    fs.resolve_forum_status(forum)
    if not fs.can_post_in_forum(forum, user):
        return jsonify({'error': 'Forum terkunci atau tidak menerima balasan baru'}), 403

    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    if not fs.check_idempotency(user.id, request_id):
        return jsonify({'error': 'Permintaan duplikat terdeteksi'}), 400
    if not fs.check_rate_limit(user.id):
        return jsonify({'error': 'Anda terlalu cepat mengirim diskusi. Silakan tunggu beberapa saat.'}), 429

    content = fs.plain_links(fs.sanitize_text(data.get('content') or ''))
    if not content:
        return jsonify({'error': 'Isi balasan wajib diisi'}), 400

    reply = ForumPost(
        forum_id=forum.id,
        author_id=user.id,
        parent_id=parent.id,
        content=content,
        post_type='reply',
        quoted_post_id=int(data['quoted_post_id']) if data.get('quoted_post_id') else None,
    )
    db.session.add(reply)
    db.session.flush()

    attachment_ids = data.get('attachment_ids') or []
    _link_attachments(reply, attachment_ids, user.id)
    _extract_and_create_mentions(reply, forum)
    db.session.commit()

    fs.log_forum_event(user, forum, 'REPLY_CREATED', {'post_id': reply.id, 'parent_id': parent.id})

    # notify parent author
    if parent.author_id != user.id:
        fs.notify(parent.author_id, user.id, 'reply',
                  f'{user.name} membalas komentar Anda di "{forum.title}".',
                  forum_id=forum.id, post_id=reply.id)

    # notify thread ancestor authors (reply to your reply), max 1 level up
    if parent.parent_id and parent.author_id != user.id:
        fs.notify(parent.author_id, user.id, 'reply_to_reply',
                  f'{user.name} membalas balasan Anda di "{forum.title}".',
                  forum_id=forum.id, post_id=reply.id)

    # presenter answered a question?
    qlink = ForumQuestion.query.filter_by(post_id=parent.id).first()
    if qlink and qlink.status == 'UNANSWERED' and (fs.is_presenter(forum, user) or fs.can_manage_forum(forum, user)):
        _mark_question_answered(qlink, user, reply)

    if _is_meaningful(content):
        fs.award_xp(user.id, 'reply_created', 5, 'post', reply.id)
    fs.evaluate_achievements(user.id)

    return jsonify({'message': 'Balasan berhasil dikirim', 'post': fs.post_payload(reply, user)}), 201


def _mark_question_answered(qlink, answerer, answer_post):
    qlink.status = 'ANSWERED'
    qlink.answered_at = datetime.utcnow()
    db.session.add(qlink)
    if not qlink.answer:
        db.session.add(ForumAnswer(
            question_id=qlink.id, presenter_id=answerer.id, answer_post_id=answer_post.id,
        ))
    db.session.commit()
    fs.log_forum_event(answerer, answer_post.forum, 'QUESTION_ANSWERED',
                       {'question_id': qlink.id, 'post_id': answer_post.id})
    if qlink.questioner_id != answerer.id:
        fs.notify(qlink.questioner_id, answerer.id, 'question_answered',
                  f'{answerer.name} menjawab pertanyaan Anda di "{answer_post.forum.title}".',
                  forum_id=answer_post.forum_id, post_id=answer_post.id)


def _link_attachments(post, attachment_ids, author_id):
    for aid in attachment_ids:
        try:
            aid = int(aid)
        except (TypeError, ValueError):
            continue
        att = ForumAttachment.query.get(aid)
        if not att or att.forum_id != post.forum_id or att.post_id is not None or att.author_id != author_id:
            continue
        att.post_id = post.id
        db.session.add(att)


@jwt_required()
def update_post(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    post = ForumPost.query.get(post_id)
    if not post or post.deleted_at is not None:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404

    data = request.get_json(silent=True) or {}
    # teacher pin
    if 'is_pinned' in data and fs.is_teacher(user) and fs.can_manage_forum(post.forum, user):
        post.is_pinned = bool(data['is_pinned'])
        db.session.commit()
        return jsonify({'message': 'Posting disematkan' if post.is_pinned else 'Semat dilepas',
                        'post': fs.post_payload(post, user)}), 200

    # author edit within 15 minutes
    if str(post.author_id) != str(user.id):
        return jsonify({'error': 'Anda tidak dapat mengubah posting orang lain'}), 403
    if post.edited_at and (datetime.utcnow() - post.edited_at).total_seconds() > 900:
        return jsonify({'error': 'Waktu edit sudah lewat (maksimal 15 menit)'}), 400
    if (datetime.utcnow() - post.created_at).total_seconds() > 900:
        return jsonify({'error': 'Waktu edit sudah lewat (maksimal 15 menit)'}), 400

    new_content = fs.plain_links(fs.sanitize_text(data.get('content') or ''))
    if not new_content:
        return jsonify({'error': 'Isi posting wajib diisi'}), 400
    post.content = new_content
    post.edited_at = datetime.utcnow()
    post.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Posting diperbarui', 'post': fs.post_payload(post, user)}), 200


@jwt_required()
def delete_post(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    post = ForumPost.query.get(post_id)
    if not post:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404
    own = str(post.author_id) == str(user.id)
    manage = fs.can_manage_forum(post.forum, user)
    if not own and not manage:
        return jsonify({'error': 'Anda tidak berhak menghapus posting ini'}), 403

    if own and post.children:
        # soft delete when it has replies
        post.deleted_at = datetime.utcnow()
        db.session.add(post)
        db.session.commit()
        return jsonify({'message': 'Posting telah dihapus', 'soft': True}), 200

    _purge_post_dependents(post)
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Posting dihapus'}), 200


@jwt_required()
def upload_forum_attachment(forum_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    forum = Forum.query.get(forum_id)
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    if not fs.can_view_forum(forum, user):
        return jsonify({'error': 'Anda tidak memiliki akses'}), 403

    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'error': 'File wajib diunggah'}), 400
    saved, err = _save_attachment(file)
    if err:
        return jsonify({'error': err}), 400

    purpose = request.form.get('purpose') or 'post'
    if purpose == 'presentation':
        if not fs.can_manage_forum(forum, user):
            os.remove(saved['path'])
            return jsonify({'error': 'Anda tidak berhak mengubah materi presentasi'}), 403
        forum.presentation_file_url = saved['url']
        forum.presentation_file_name = saved['original']
        forum.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'message': 'File presentasi diunggah',
                        'url': saved['url'], 'name': saved['original']}), 201

    att = ForumAttachment(
        forum_id=forum.id,
        author_id=user.id,
        original_name=saved['original'],
        file_name=saved['name'],
        file_size=saved['size'],
        file_type=saved['type'],
        file_url=saved['url'],
    )
    db.session.add(att)
    db.session.commit()
    return jsonify({'message': 'Lampiran diunggah', 'attachment': {
        'id': att.id, 'original_name': att.original_name, 'file_name': att.file_name,
        'file_size': att.file_size, 'file_type': att.file_type, 'file_url': att.file_url,
    }}), 201


# ============================================================
# REACTIONS
# ============================================================

@jwt_required()
def toggle_reaction(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    post = ForumPost.query.get(post_id)
    if not post or post.deleted_at is not None:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404
    forum = post.forum
    if forum.status == 'CLOSED':
        return jsonify({'error': 'Forum ditutup, reaksi tidak dapat diubah'}), 403
    if not fs.can_view_forum(forum, user):
        return jsonify({'error': 'Anda tidak memiliki akses'}), 403

    data = request.get_json(silent=True) or {}
    reaction_type = data.get('reaction_type')
    if reaction_type not in REACTION_TYPES:
        return jsonify({'error': 'Reaksi tidak valid'}), 400

    existing = ForumReaction.query.filter_by(post_id=post.id, user_id=user.id).first()
    if existing:
        if existing.reaction_type == reaction_type:
            db.session.delete(existing)
            db.session.commit()
            return jsonify({'message': 'Reaksi dihapus', 'reaction': None}), 200
        existing.reaction_type = reaction_type
        db.session.commit()
        return jsonify({'message': 'Reaksi diperbarui', 'reaction': reaction_type}), 200

    db.session.add(ForumReaction(post_id=post.id, user_id=user.id, reaction_type=reaction_type))
    db.session.commit()
    fs.log_forum_event(user, forum, 'REACTION_ADDED', {'post_id': post.id, 'reaction_type': reaction_type})
    if post.author_id != user.id:
        fs.notify(post.author_id, user.id, 'reaction',
                  f'{user.name} memberi reaksi pada posting Anda di "{forum.title}".',
                  forum_id=forum.id, post_id=post.id)
    return jsonify({'message': 'Reaksi ditambahkan', 'reaction': reaction_type}), 200


@jwt_required()
def remove_reaction(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    existing = ForumReaction.query.filter_by(post_id=post_id, user_id=user.id).first()
    if not existing:
        return jsonify({'message': 'Tidak ada reaksi'}), 200
    db.session.delete(existing)
    db.session.commit()
    return jsonify({'message': 'Reaksi dihapus'}), 200


# ============================================================
# PRESENTER QUESTIONS
# ============================================================

@jwt_required()
def create_question(forum_id=None):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json(silent=True) or {}
    forum = Forum.query.get(forum_id or data.get('forum_id'))
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    fs.resolve_forum_status(forum)
    if not fs.can_post_in_forum(forum, user):
        return jsonify({'error': 'Forum terkunci atau tidak menerima pertanyaan'}), 403
    if forum.type != 'PRESENTATION':
        return jsonify({'error': 'Hanya forum presentasi yang menerima pertanyaan presenter'}), 400

    request_id = data.get('request_id')
    if not fs.check_idempotency(user.id, request_id):
        return jsonify({'error': 'Permintaan duplikat terdeteksi'}), 400
    if not fs.check_rate_limit(user.id):
        return jsonify({'error': 'Anda terlalu cepat mengirim diskusi. Silakan tunggu beberapa saat.'}), 429

    content = fs.plain_links(fs.sanitize_text(data.get('content') or ''))
    if not content:
        return jsonify({'error': 'Pertanyaan wajib diisi'}), 400

    post = ForumPost(forum_id=forum.id, author_id=user.id, content=content, post_type='question')
    db.session.add(post)
    db.session.flush()

    presenter_id = int(data['presenter_id']) if data.get('presenter_id') else (forum.presenter_id or None)
    db.session.add(ForumQuestion(
        forum_id=forum.id, post_id=post.id, questioner_id=user.id, presenter_id=presenter_id,
    ))
    _extract_and_create_mentions(post, forum)
    db.session.commit()

    fs.log_forum_event(user, forum, 'QUESTION_CREATED', {'post_id': post.id})
    fs.award_xp(user.id, 'question_created', 5, 'post', post.id)
    fs.evaluate_achievements(user.id)
    if forum.presenter_id and forum.presenter_id != user.id:
        fs.notify(forum.presenter_id, user.id, 'presenter_question',
                  f'{user.name} mengajukan pertanyaan di "{forum.title}".',
                  forum_id=forum.id, post_id=post.id)

    return jsonify({'message': 'Pertanyaan dikirim', 'post': fs.post_payload(post, user)}), 201


@jwt_required()
def answer_question(question_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    question = ForumQuestion.query.get(question_id)
    if not question:
        return jsonify({'error': 'Pertanyaan tidak ditemukan'}), 404
    forum = question.forum
    if not fs.can_answer_question(forum, user):
        return jsonify({'error': 'Hanya presenter atau guru yang dapat menjawab'}), 403

    data = request.get_json(silent=True) or {}
    request_id = data.get('request_id')
    if not fs.check_idempotency(user.id, request_id):
        return jsonify({'error': 'Permintaan duplikat terdeteksi'}), 400
    if not fs.check_rate_limit(user.id):
        return jsonify({'error': 'Anda terlalu cepat mengirim diskusi. Silakan tunggu beberapa saat.'}), 429

    content = fs.plain_links(fs.sanitize_text(data.get('content') or ''))
    if not content:
        return jsonify({'error': 'Jawaban wajib diisi'}), 400

    answer_post = ForumPost(
        forum_id=forum.id, author_id=user.id, parent_id=question.post_id,
        content=content, post_type='answer',
    )
    db.session.add(answer_post)
    db.session.flush()
    _mark_question_answered(question, user, answer_post)
    db.session.commit()

    if _is_meaningful(content):
        fs.award_xp(user.id, 'answer_created', 5, 'post', answer_post.id)
    fs.evaluate_achievements(user.id)

    return jsonify({'message': 'Jawaban dikirim', 'post': fs.post_payload(answer_post, user)}), 201


# ============================================================
# FEEDBACK & BEST ANSWER
# ============================================================

@jwt_required()
def create_feedback(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat memberikan feedback'}), 403
    post = ForumPost.query.get(post_id)
    if not post or post.deleted_at is not None:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404
    if not fs.can_manage_forum(post.forum, user):
        return jsonify({'error': 'Anda tidak dapat memberi feedback pada forum ini'}), 403

    data = request.get_json(silent=True) or {}
    feedback_text = fs.sanitize_text(data.get('feedback') or '')
    if not feedback_text:
        return jsonify({'error': 'Feedback wajib diisi'}), 400

    fb = ForumFeedback.query.filter_by(post_id=post.id).first()
    if fb:
        fb.feedback = feedback_text
        fb.updated_at = datetime.utcnow()
    else:
        fb = ForumFeedback(post_id=post.id, teacher_id=user.id, feedback=feedback_text)
        db.session.add(fb)
    db.session.commit()

    fs.log_forum_event(user, post.forum, 'TEACHER_FEEDBACK_CREATED', {'post_id': post.id})
    if post.author_id != user.id:
        fs.notify(post.author_id, user.id, 'teacher_feedback',
                  f'Guru memberikan feedback pada jawaban Anda di "{post.forum.title}".',
                  forum_id=post.forum_id, post_id=post.id)
    return jsonify({'message': 'Feedback disimpan', 'feedback': {
        'teacher_id': user.id, 'teacher_name': user.name, 'feedback': fb.feedback,
        'created_at': fb.created_at.isoformat() + 'Z',
    }}), 201


@jwt_required()
def mark_best_answer(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat memilih jawaban terbaik'}), 403
    post = ForumPost.query.get(post_id)
    if not post or post.deleted_at is not None:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404
    if not fs.can_manage_forum(post.forum, user):
        return jsonify({'error': 'Anda tidak dapat mengelola forum ini'}), 403

    root = post if post.parent_id is None else (post.parent if post.parent.parent_id is None else post.parent.parent)
    root_id = root.id
    # clear previous best answers in the same thread
    siblings = [p for p in root.children if p.parent_id == root_id] if root.parent_id is None else []
    ForumPost.query.filter_by(forum_id=post.forum_id, is_best_answer=True).filter(
        ForumPost.parent_id.in_([root_id]) | (ForumPost.id == root_id)
    ).update({'is_best_answer': False})
    db.session.commit()

    post.is_best_answer = True
    db.session.commit()

    fs.log_forum_event(user, post.forum, 'BEST_ANSWER_SELECTED', {'post_id': post.id})
    if post.author_id != user.id:
        fs.notify(post.author_id, user.id, 'best_answer',
                  f'Jawaban Anda ditandai sebagai Best Answer di "{post.forum.title}".',
                  forum_id=post.forum_id, post_id=post.id)
    fs.award_xp(post.author_id, 'best_answer', 15, 'post', post.id)
    fs.evaluate_achievements(post.author_id)
    return jsonify({'message': 'Jawaban terbaik ditandai', 'post_id': post.id}), 200


# ============================================================
# LOCK / UNLOCK
# ============================================================

@jwt_required()
def lock_forum(forum_id):
    return _set_lock(forum_id, 'CLOSED')


@jwt_required()
def unlock_forum(forum_id):
    return _set_lock(forum_id, 'ACTIVE')


def _set_lock(forum_id, status):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    forum = Forum.query.get(forum_id)
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    if not fs.can_manage_forum(forum, user):
        return jsonify({'error': 'Anda tidak berhak mengunci forum ini'}), 403
    forum.status = status
    forum.updated_at = datetime.utcnow()
    db.session.add(ForumModerationLog(
        moderator_id=user.id, action='LOCK' if status == 'CLOSED' else 'UNLOCK', forum_id=forum.id,
    ))
    db.session.commit()
    return jsonify({'message': 'Forum dikunci' if status == 'CLOSED' else 'Forum dibuka kembali',
                    'status': forum.status}), 200


# ============================================================
# REPORT & MODERATION
# ============================================================

@jwt_required()
def report_post(post_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    post = ForumPost.query.get(post_id)
    if not post or post.deleted_at is not None:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404
    if not fs.can_view_forum(post.forum, user):
        return jsonify({'error': 'Anda tidak memiliki akses'}), 403

    data = request.get_json(silent=True) or {}
    reason = data.get('reason')
    if reason not in REPORT_REASONS:
        return jsonify({'error': 'Alasan laporan tidak valid'}), 400

    existing = ForumReport.query.filter_by(post_id=post.id, reported_by=user.id).first()
    if existing:
        return jsonify({'error': 'Anda sudah melaporkan posting ini'}), 400

    db.session.add(ForumReport(
        post_id=post.id, reported_by=user.id, reason=reason,
        description=fs.sanitize_text(data.get('description') or ''),
    ))
    db.session.commit()
    return jsonify({'message': 'Laporan terkirim. Terima kasih atas partisipasi Anda.'}), 201


@jwt_required()
def teacher_moderation_queue():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat mengakses moderasi'}), 403

    forums = [f for f in Forum.query.all() if fs.can_manage_forum(f, user)]
    forum_ids = [f.id for f in forums]

    reports = []
    if forum_ids:
        rows = ForumReport.query.filter(
            ForumReport.status == 'PENDING', ForumReport.post_id.in_(
                db.session.query(ForumPost.id).filter(ForumPost.forum_id.in_(forum_ids))
            )
        ).order_by(ForumReport.created_at.asc()).limit(100).all()
        for r in rows:
            reports.append({
                'id': r.id, 'post_id': r.post_id, 'post_content': r.post.content[:300],
                'forum_title': r.post.forum.title if r.post.forum else None,
                'reason': r.reason, 'description': r.description,
                'reported_by': r.reporter.name if r.reporter else None,
                'created_at': r.created_at.isoformat() + 'Z' if r.created_at else None,
                'author_name': r.post.author.name if r.post.author else None,
            })

    unanswered = []
    if forum_ids:
        qrows = ForumQuestion.query.filter(
            ForumQuestion.status == 'UNANSWERED', ForumQuestion.forum_id.in_(forum_ids)
        ).order_by(ForumQuestion.created_at.asc()).limit(100).all()
        for q in qrows:
            unanswered.append({
                'id': q.id, 'question': q.post.content[:300],
                'forum_title': q.forum.title if q.forum else None,
                'questioner': q.questioner.name if q.questioner else None,
                'presenter_name': q.presenter.name if q.presenter else None,
                'created_at': q.created_at.isoformat() + 'Z' if q.created_at else None,
            })

    active = sum(1 for f in forums if f.status == 'ACTIVE')
    closed = sum(1 for f in forums if f.status == 'CLOSED')

    return jsonify({
        'reported_posts': reports,
        'unanswered_questions': unanswered,
        'active_forums': active,
        'closed_forums': closed,
        'forums': [{'id': f.id, 'title': f.title, 'type': f.type, 'status': f.status} for f in forums],
    }), 200


@jwt_required()
def moderation_action(post_id, action):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat moderasi'}), 403
    post = ForumPost.query.get(post_id)
    if not post:
        return jsonify({'error': 'Posting tidak ditemukan'}), 404
    if not fs.can_manage_forum(post.forum, user):
        return jsonify({'error': 'Anda tidak dapat memoderasi forum ini'}), 403

    data = request.get_json(silent=True) or {}
    reason = fs.sanitize_text(data.get('reason') or '')

    if action == 'HIDE':
        post.deleted_at = post.deleted_at or datetime.utcnow()
    elif action == 'RESTORE':
        post.deleted_at = None
    elif action == 'DELETE':
        _purge_post_dependents(post)
        db.session.delete(post)
    else:
        return jsonify({'error': 'Aksi tidak valid'}), 400

    db.session.add(ForumModerationLog(
        moderator_id=user.id, action=action, post_id=post.id, reason=reason,
    ))
    # resolve matching reports
    ForumReport.query.filter_by(post_id=post.id, status='PENDING').update({
        'status': 'ACTION_TAKEN' if action == 'DELETE' else 'REVIEWED',
        'reviewed_by': user.id, 'reviewed_at': datetime.utcnow(),
    })
    db.session.commit()
    return jsonify({'message': f'Aksi moderasi "{action}" berhasil'}), 200


# ============================================================
# SETTINGS & SUGGEST
# ============================================================

@jwt_required()
def get_forum_settings():
    return jsonify({'allow_student_forum_creation': fs.allow_student_creation()}), 200


@jwt_required()
def update_forum_settings():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat mengubah pengaturan'}), 403
    data = request.get_json(silent=True) or {}
    if 'allow_student_forum_creation' in data:
        fs.set_setting('allow_student_forum_creation', 'true' if data['allow_student_forum_creation'] else 'false')
    return jsonify({'message': 'Pengaturan forum diperbarui',
                    'allow_student_forum_creation': fs.allow_student_creation()}), 200


@jwt_required()
def suggest_mentions():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    q = (request.args.get('q') or '').strip().lower()
    forum_id = request.args.get('forum_id', type=int)
    members = set()
    if forum_id:
        forum = Forum.query.get(forum_id)
        if forum and fs.can_view_forum(forum, user):
            members = _course_member_ids(forum)
    else:
        enrolled = Enrollment.query.filter_by(student_id=user.id).all()
        course_ids = [e.course_id for e in enrolled]
        if course_ids:
            for eid in Enrollment.query.filter(Enrollment.course_id.in_(course_ids)).all():
                members.add(eid.student_id)
        for cid in course_ids:
            course = Course.query.get(cid)
            if course:
                members.add(course.teacher_id)
    members.discard(user.id)
    if not members:
        return jsonify({'users': []}), 200
    rows = User.query.filter(User.id.in_(members))
    if q:
        rows = rows.filter(db.func.lower(User.name).like(f'%{q}%'))
    users = [{'id': u.id, 'name': u.name, 'role': u.role} for u in rows.limit(20).all()]
    return jsonify({'users': users}), 200


# ============================================================
# ANALYTICS
# ============================================================

@jwt_required()
def teacher_forum_analytics():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role not in ('teacher', 'admin'):
        return jsonify({'error': 'Hanya guru yang dapat mengakses analitik forum'}), 403

    forums = [f for f in Forum.query.all() if fs.can_manage_forum(f, user)]
    total_participants = 0
    total_questions = 0
    total_replies = 0
    unanswered = 0
    topic_counter = {}
    for f in forums:
        root_authors = {p.author_id for p in f.posts if p.deleted_at is None}
        total_participants = max(total_participants, len(root_authors))
        total_questions += len(f.questions)
        unanswered += sum(1 for q in f.questions if q.status == 'UNANSWERED')
        total_replies += sum(1 for p in f.posts if p.parent_id is not None and p.deleted_at is None)
        if f.topic:
            topic_counter[f.topic] = topic_counter.get(f.topic, 0) + 1

    most_discussed = sorted(topic_counter.items(), key=lambda x: x[1], reverse=True)[:8]

    return jsonify({
        'forums_count': len(forums),
        'active_forums': sum(1 for f in forums if f.status == 'ACTIVE'),
        'closed_forums': sum(1 for f in forums if f.status == 'CLOSED'),
        'questions': total_questions,
        'replies': total_replies,
        'unanswered_questions': unanswered,
        'participants': total_participants,
        'most_discussed_topics': [{'topic': t, 'count': c} for t, c in most_discussed],
        'forums': [{'id': f.id, 'title': f.title, 'type': f.type, 'status': f.status,
                    'questions': len(f.questions), 'replies': sum(1 for p in f.posts if p.parent_id is not None and p.deleted_at is None)} for f in forums],
    }), 200


@jwt_required()
def student_forum_analytics():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    if user.role != 'student':
        return jsonify({'error': 'Endpoint ini khusus siswa'}), 403

    stats = fs.user_stats(user.id)
    visible = _visible_forums(user)
    participated = [f for f in visible if any(p.author_id == user.id for p in f.posts)]
    my_answers = ForumPost.query.filter_by(author_id=user.id, is_best_answer=True).count()
    participation = round(len(participated) / len(visible) * 100, 1) if visible else 0.0
    return jsonify({
        'my_discussions': stats['forums_created'],
        'my_questions': stats['questions'],
        'my_replies': stats['replies'],
        'best_answers': stats['best_answers'],
        'xp': stats['xp'],
        'level': stats['level'],
        'forum_participation': participation,
        'participated_forums': len(participated),
        'visible_forums': len(visible),
        'achievements': [{
            'code': a.achievement.code, 'label': a.achievement.label,
            'description': a.achievement.description, 'icon': a.achievement.icon,
            'awarded_at': a.awarded_at.isoformat() + 'Z' if a.awarded_at else None,
        } for a in user.achievements],
    }), 200


# ============================================================
# NOTIFICATIONS
# ============================================================

@jwt_required()
def get_notifications():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    limit = min(request.args.get('limit', 30, type=int), 100)
    rows = Notification.query.filter_by(user_id=user.id).order_by(
        Notification.created_at.desc()).limit(limit).all()
    unread = Notification.query.filter_by(user_id=user.id, is_read=False).count()
    return jsonify({
        'unread': unread,
        'notifications': [{
            'id': n.id, 'notification_type': n.notification_type, 'message': n.message,
            'forum_id': n.forum_id, 'post_id': n.post_id, 'is_read': n.is_read,
            'actor_name': n.actor.name if n.actor else None,
            'created_at': n.created_at.isoformat() + 'Z' if n.created_at else None,
        } for n in rows],
    }), 200


@jwt_required()
def mark_notification_read(notification_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    n = Notification.query.filter_by(id=notification_id, user_id=user.id).first()
    if not n:
        return jsonify({'error': 'Notifikasi tidak ditemukan'}), 404
    n.is_read = True
    db.session.commit()
    return jsonify({'message': 'Dibaca'}), 200


@jwt_required()
def mark_all_notifications_read():
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    Notification.query.filter_by(user_id=user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return jsonify({'message': 'Semua notifikasi ditandai dibaca'}), 200


# ============================================================
# PRESENTER DASHBOARD
# ============================================================

@jwt_required()
def presenter_dashboard(forum_id):
    user = _current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    forum = Forum.query.get(forum_id)
    if not forum:
        return jsonify({'error': 'Forum tidak ditemukan'}), 404
    if forum.type != 'PRESENTATION':
        return jsonify({'error': 'Bukan forum presentasi'}), 400
    if not fs.can_view_forum(forum, user):
        return jsonify({'error': 'Anda tidak memiliki akses'}), 403
    is_presenter = fs.is_presenter(forum, user)

    questions = ForumQuestion.query.filter_by(forum_id=forum.id).order_by(ForumQuestion.created_at.asc()).all()
    return jsonify({
        'forum': fs.forum_payload(forum, user),
        'is_presenter': is_presenter,
        'questions_total': len(questions),
        'answered': sum(1 for q in questions if q.status == 'ANSWERED'),
        'unanswered': sum(1 for q in questions if q.status == 'UNANSWERED'),
        'questions': [{
            'id': q.id, 'post_id': q.post_id, 'status': q.status,
            'content': q.post.content, 'questioner': q.questioner.name if q.questioner else None,
            'created_at': q.created_at.isoformat() + 'Z' if q.created_at else None,
            'answer': q.answer.answer_post.content if q.answer else None,
            'can_answer': is_presenter or fs.can_manage_forum(forum, user),
        } for q in questions],
    }), 200
