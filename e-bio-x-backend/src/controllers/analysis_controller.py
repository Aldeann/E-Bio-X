from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from src.models.submission import Submission
from src.models.quiz import Quiz
from src.models.answer import Answer
from src.models.question import Question
from src.models.option import Option
from src.models.user import User
from src.services.analysis_service import kmeans, decision_tree


def _analysis_user():
    uid = get_jwt_identity()
    return User.query.get(uid) if uid else None


def _can_analyze_quiz(quiz, user):
    if not user:
        return False
    if user.role == 'admin':
        return True
    if user.role == 'teacher':
        if quiz.course_id and quiz.course:
            return str(quiz.course.teacher_id) == str(user.id)
        return True
    return False

@jwt_required()
def analyze_quiz(quiz_id):
    user = _analysis_user()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'message': 'Quiz not found'}), 404
    if not _can_analyze_quiz(quiz, user):
        return jsonify({'message': 'Anda tidak berhak menganalisis kuis ini'}), 403

    result = kmeans(quiz_id)
    if isinstance(result, tuple): 
        return jsonify(result[0]), result[1]

    return jsonify({
        'message': 'Analysis successfull'
    }), 200

@jwt_required()
def get_analyze(quiz_id):
    user = _analysis_user()
    if not user:
        return jsonify({'message': 'User not found'}), 404
    quiz = Quiz.query.get(quiz_id)
    if not quiz:
        return jsonify({'message': 'Quiz not found'}), 404
    if not _can_analyze_quiz(quiz, user):
        return jsonify({'message': 'Anda tidak berhak menganalisis kuis ini'}), 403

    result, rules, highest, lowest, fastest, slowest, avg_score, hardest, easiest = statistics(quiz_id)
    if result is None:
        return jsonify({'message': 'Data nilai belum cukup untuk analisis'}), 200
    
    return jsonify({
        'quiz_title': quiz.title,
        'total_questions': len(quiz.questions),
        'total_students': len(result),
        'clusters': result,
        'decision_tree_rules': rules,
        'highest_score': {
            'nama': highest['nama'],
            'score': highest['score'],
            'cluster': highest['cluster'],
            'work_time': highest['work_time']
        },
        'lowest_score': {
            'nama': lowest['nama'],
            'score': lowest['score'],
            'cluster': lowest['cluster'],
            'work_time': lowest['work_time']
        },
        'fastest_work_time': {
            'nama': fastest['nama'],
            'score': fastest['score'],
            'cluster': fastest['cluster'],
            'work_time': fastest['work_time']
        },
        'slowest_work_time': {
            'nama': slowest['nama'],
            'score': slowest['score'],
            'cluster': slowest['cluster'],
            'work_time': slowest['work_time']
        },
        'average_score': avg_score,
        'hardest_question': {
            'question': hardest['question_text'],
            'correct_answers': hardest['correct_answers'],
            'total_answers': hardest['total_answers']
        } if hardest else None,
        'easiest_question': {
            'question': easiest['question_text'],
            'correct_answers': easiest['correct_answers'],
            'total_answers': easiest['total_answers']
        } if easiest else None
    })

def statistics(quiz_id):
    submissions = Submission.query.filter_by(quiz_id=quiz_id).all()
    if not submissions:
       return None, None, None, None, None, None, None, None, None
   
    rules = decision_tree(quiz_id)
    if isinstance(rules, dict):
       return None, None, None, None, None, None, None, None, None

    result = []
    for s in submissions:
        result.append({
            'id': s.id,
            'nama': s.student.name,
            'score': s.score,
            'work_time': s.work_time.strftime('%H:%M:%S') if s.work_time else None,
            'submitted_at': s.submitted_at.strftime('%Y-%m-%d %H:%M:%S'),
            'cluster': int(s.cluster) if s.cluster is not None else None
        })
        
    from collections import defaultdict

    cluster_scores = defaultdict(list)
    for item in result:
        if item['cluster'] is not None:
            cluster_scores[item['cluster']].append(item['score'])

    cluster_avg = []
    for cluster_id, scores in cluster_scores.items():
        avg = sum(scores) / len(scores)
        cluster_avg.append({'cluster': cluster_id, 'avg_score': avg})

    cluster_avg.sort(key=lambda x: x['avg_score'], reverse=True)

    cluster_label_mapping = {}
    labels = ['Unggul', 'Rata-rata', 'Butuh bimbingan']
    for i, cluster in enumerate(cluster_avg):
        cluster_label_mapping[cluster['cluster']] = labels[i]

    for item in result:
        if item['cluster'] is not None:
            item['cluster'] = cluster_label_mapping.get(item['cluster'], 'Tidak terkategorikan')
        else:
            item['cluster'] = 'Tidak terkategorikan'


    # Nilai tertinggi & terendah
    highest = max(result, key=lambda x: x['score'])
    lowest = min(result, key=lambda x: x['score'])

    # Work time tercepat & terlambat
    timed = [x for x in result if x['work_time']]
    fastest = min(timed, key=lambda x: x['work_time']) if timed else (result[0] if result else None)
    slowest = max(timed, key=lambda x: x['work_time']) if timed else (result[0] if result else None)

    # Rata-rata nilai
    avg_score = sum(item['score'] for item in result) / len(result)

    # Soal tersulit dan termudah
    questions = Question.query.filter_by(quiz_id=quiz_id).all()
    question_stats = []

    for question in questions:
        total_answers = Answer.query.filter_by(question_id=question.id).count()

        correct_option_ids = [o.id for o in Option.query.filter_by(question_id=question.id, is_correct=True).all()]

        correct_answers = Answer.query.filter(
            Answer.question_id == question.id,
            Answer.option_id.in_(correct_option_ids)
        ).count()

        question_stats.append({
            'question_id': question.id,
            'question_text': question.text,
            'total_answers': total_answers,
            'correct_answers': correct_answers
        })

    # cari soal tersulit & termudah
    hardest = min(question_stats, key=lambda x: x['correct_answers']) if question_stats else None
    easiest = max(question_stats, key=lambda x: x['correct_answers']) if question_stats else None

    return result, rules, highest, lowest, fastest, slowest, avg_score, hardest, easiest 