export function uploadFile({ url, token, file, onProgress }) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.timeout = 120000;

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    };

    xhr.onload = () => {
      let body;
      try {
        body = JSON.parse(xhr.responseText);
      } catch {
        body = { error: "Gagal mengurai respons server" };
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(body);
      } else {
        reject(body);
      }
    };

    xhr.onerror = () => reject({ error: "Terjadi kesalahan jaringan" });
    xhr.ontimeout = () => reject({ error: "Waktu upload habis" });

    const form = new FormData();
    form.append("file", file);
    xhr.send(form);
  });
}

export function fileSize(bytes) {
  if (!bytes && bytes !== 0) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export const allowedFileTypes = [".pdf", ".jpg", ".jpeg", ".png", ".webp", ".mp4"];