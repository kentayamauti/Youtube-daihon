/**
 * 相談の希望日時を3つ選んでもらい、Googleカレンダーに「仮」の予定として入れるスクリプト
 *
 * できること:
 *  - 申し込みフォームに「第1〜第3希望の日時」の質問を追加する（「ご希望の相談時間帯」の質問は外す）
 *  - 申し込みが来たら、3つの候補をカレンダーに【仮】の予定（黄色）として入れる
 *  - その時間にほかの予定が入っているかを調べて、メールで知らせる（○空いている／✕予定あり）
 *  - Ykkn 山内が1つ選んでお客さんに連絡したら、カレンダーで残り2つを消し、選んだ予定の【仮】を外す
 *
 * 使い方（初回だけ・5分）:
 *  1. https://script.google.com を開き、create_form.gs を実行したときのプロジェクトを開く
 *     （見つからなければ「新しいプロジェクト」でもOK）
 *  2. 左の「ファイル」の＋ →「スクリプト」で新しいファイルを作り、このファイルの中身を貼り付けて保存
 *  3. 下の FORM_EDIT_URL に、フォームの編集用URL（https://docs.google.com/forms/d/〜/edit）を貼る
 *  4. 上部の関数選択で「setupCalendarBooking」を選び「実行」
 *  5. 権限の確認が出たら、ご自身のGoogleアカウントで許可（カレンダー・フォーム・メール）
 */

const CAL_CONFIG = {
  FORM_EDIT_URL: '', // フォームの編集用URL
  calendarId: '', // 空なら、いつも使っているカレンダー
  durationMinutes: 60, // カレンダーに押さえる時間（相談30分＋延長・準備の余裕）
  notifyEmail: '', // 空なら、スクリプトを実行した人のアドレス
};

const CANDIDATE_TITLES = ['ご希望の日時（第1希望）', 'ご希望の日時（第2希望）', 'ご希望の日時（第3希望）'];
const OLD_TIME_ITEM_TITLE = 'ご希望の相談時間帯（複数選択可）';

function setupCalendarBooking() {
  if (!CAL_CONFIG.FORM_EDIT_URL) throw new Error('FORM_EDIT_URL にフォームの編集用URLを貼ってください');
  const form = FormApp.openByUrl(CAL_CONFIG.FORM_EDIT_URL);
  const items = form.getItems();

  if (!items.some(i => i.getTitle() === CANDIDATE_TITLES[0])) {
    // 「個人情報の取り扱い」の直前に入れる
    const privacy = items.find(i => i.getTitle() === '個人情報の取り扱い');
    let insertAt = privacy ? privacy.getIndex() : items.length;

    CANDIDATE_TITLES.forEach((title, n) => {
      const item = form.addDateTimeItem()
          .setTitle(title)
          .setHelpText(n === 0
              ? 'ご都合のよい日時を3つお選びください。この中から1つを選んで、Ykkn 山内からご連絡します（2営業日以降の日時でお願いします）。'
              : '')
          .setRequired(true);
      form.moveItem(item.getIndex(), insertAt++);
    });

    const oldItem = form.getItems().find(i => i.getTitle() === OLD_TIME_ITEM_TITLE);
    if (oldItem) form.deleteItem(oldItem);
  }

  const exists = ScriptApp.getProjectTriggers()
      .some(t => t.getHandlerFunction() === 'addCandidatesToCalendar');
  if (!exists) {
    ScriptApp.newTrigger('addCandidatesToCalendar').forForm(form).onFormSubmit().create();
  }
  Logger.log('設定が終わりました。フォームを開いて、第1〜第3希望の質問が入っているか確認してください。');
}

function addCandidatesToCalendar(e) {
  const answers = {};
  e.response.getItemResponses().forEach(r => {
    const v = r.getResponse();
    answers[r.getItem().getTitle()] = Array.isArray(v) ? v.join(', ') : v;
  });

  const name = answers['お名前'] || '（お名前なし）';
  const menu = answers['お問い合わせの種類'] || '';
  const calendar = CAL_CONFIG.calendarId
      ? CalendarApp.getCalendarById(CAL_CONFIG.calendarId)
      : CalendarApp.getDefaultCalendar();

  const detail = Object.keys(answers).map(k => '■ ' + k + '\n' + answers[k]).join('\n\n');
  const report = [];

  CANDIDATE_TITLES.forEach((title, n) => {
    const start = parseDateTime(answers[title]);
    if (!start) return;
    const end = new Date(start.getTime() + CAL_CONFIG.durationMinutes * 60 * 1000);

    const busy = calendar.getEvents(start, end).filter(ev => !ev.getTitle().startsWith('【仮】'));
    const event = calendar.createEvent(
        '【仮】' + name + '様 第' + (n + 1) + '希望' + (menu ? '（' + menu + '）' : ''),
        start, end, { description: detail });
    event.setColor(CalendarApp.EventColor.YELLOW);

    report.push('第' + (n + 1) + '希望　' + Utilities.formatDate(start, Session.getScriptTimeZone(), 'M/d(E) HH:mm') +
        '　' + (busy.length ? '✕ 予定あり（' + busy.map(ev => ev.getTitle()).join('、') + '）' : '○ 空いています'));
  });

  const to = CAL_CONFIG.notifyEmail || Session.getEffectiveUser().getEmail();
  MailApp.sendEmail(to, '【相談の希望日時】' + name + '様',
      report.join('\n') +
      '\n\nカレンダーに【仮】の予定（黄色）を入れました。' +
      '\n1つ選んでお客さんに連絡したら、残りの予定を消し、選んだ予定の【仮】を外してください。');
}

// フォームの日時の回答（"2026-10-12 20:00" の形）を Date にする
function parseDateTime(value) {
  const m = /(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})/.exec(value || '');
  if (!m) return null;
  return new Date(+m[1], +m[2] - 1, +m[3], +m[4], +m[5]);
}
