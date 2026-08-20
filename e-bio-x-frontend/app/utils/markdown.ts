export function escapeHtml(text = "") {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Render a safe markdown subset: **bold**, *italic*, `code`, links [text](url),
// and line breaks. Input must already be plain text (backend strips HTML/XSS).
export function renderMarkdown(text = "") {
  let s = escapeHtml(text);
  // [label](url) links -> only http(s) targets
  s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-green-600 dark:text-green-400 underline break-all">$1</a>');
  // bare http(s) urls
  s = s.replace(/(^|\s)(https?:\/\/[^\s<>"')\]]+)/g, '$1<a href="$2" target="_blank" rel="noopener noreferrer" class="text-green-600 dark:text-green-400 underline break-all">$2</a>');
  // code
  s = s.replace(/`([^`]+)`/g, '<code class="bg-gray-100 dark:bg-gray-700 px-1.5 py-0.5 rounded text-xs">$1</code>');
  // bold
  s = s.replace(/\*\*([^*]+)\*\*/g, "<strong class=\"font-semibold\">$1</strong>");
  // italic
  s = s.replace(/(^|\s)\*([^*\n]+)\*(?=\s|$)/g, "$1<em class=\"italic\">$2</em>");
  // blockquotes
  s = s.replace(/^&gt;\s?(.*)$/gm, '<blockquote class="border-l-4 border-green-300 dark:border-green-800 pl-3 my-1 text-gray-600 dark:text-gray-300">$1</blockquote>');
  // line breaks
  return s.replace(/\n/g, "<br>");
}