/**
 * 個別相談 申し込みフォームを自動作成する Google Apps Script
 *
 * 使い方（5分）:
 *  1. https://script.google.com を開き「新しいプロジェクト」
 *  2. このファイルの中身をすべて貼り付けて保存
 *  3. 上部の関数選択で「createConsultationForm」を選び「実行」
 *  4. 初回は権限の確認が出るので、ご自身のGoogleアカウントで許可
 *  5. 実行ログに表示される「回答用URL」を LP の FORM_URL に貼る
 *
 * 回答はフォームに紐づくスプレッドシートにも自動で記録されます。
 * 回答があるたびにメール通知を受け取る設定もこのスクリプトで行います。
 */

const CONFIG = {
  title: '個別相談 お申し込みフォーム（セミナー受講者限定）',
  description:
    '「ゼロから始めるYouTubeチャンネル運用セミナー」にご参加いただき、ありがとうございました。\n' +
    '受講者限定の個別相談（30分／通常30,000円 → 特別価格15,000円・税込）のお申し込みフォームです。\n' +
    '2営業日以内に、ご入力いただいたメールアドレスへ日程調整のご連絡をいたします。',
  confirmationMessage:
    'お申し込みありがとうございました。2営業日以内にメールでご連絡いたします。',
  notifyEmail: '', // 通知を受け取るメールアドレス（空ならスクリプト実行者のアドレス）
};

function createConsultationForm() {
  const form = FormApp.create(CONFIG.title);
  form.setDescription(CONFIG.description)
      .setConfirmationMessage(CONFIG.confirmationMessage)
      .setCollectEmail(false)
      .setAllowResponseEdits(false)
      .setProgressBar(false);

  form.addMultipleChoiceItem()
      .setTitle('お問い合わせの種類')
      .setChoiceValues(['個別相談（特別価格15,000円）を申し込む', '申し込む前に質問したい'])
      .setRequired(true);

  form.addTextItem().setTitle('お名前').setRequired(true);
  form.addTextItem().setTitle('会社名・屋号（個人の方は空欄でOK）');

  const emailValidation = FormApp.createTextValidation()
      .requireTextIsEmail()
      .setHelpText('メールアドレスの形式で入力してください')
      .build();
  form.addTextItem().setTitle('メールアドレス').setValidation(emailValidation).setRequired(true);
  form.addTextItem().setTitle('電話番号（任意）');

  form.addMultipleChoiceItem()
      .setTitle('YouTubeチャンネルの状況')
      .setChoiceValues(['すでに運営している', 'これから始める予定', 'まだ検討中'])
      .setRequired(true);

  form.addTextItem()
      .setTitle('チャンネルURL（運営中の方）／予定しているジャンル（これからの方）');

  form.addCheckboxItem()
      .setTitle('YouTubeで一番実現したいこと（複数選択可）')
      .setChoiceValues(['お店・会社の集客', '商品・サービスの販売', '広告収益', 'ブランディング・認知'])
      .showOtherOption(true)
      .setRequired(true);

  form.addParagraphTextItem()
      .setTitle('今いちばん困っていること・相談したいこと')
      .setRequired(true);

  form.addCheckboxItem()
      .setTitle('ご希望の相談時間帯（複数選択可）')
      .setChoiceValues(['平日 昼（10〜17時）', '平日 夜（19〜22時）', '土日祝 昼', '土日祝 夜']);

  form.addMultipleChoiceItem()
      .setTitle('個人情報の取り扱い')
      .setHelpText('ご入力いただいた情報は、ご連絡・個別相談の実施のためにのみ利用します。')
      .setChoiceValues(['同意する'])
      .setRequired(true);

  // 回答を記録するスプレッドシートを作成して紐づけ
  const ss = SpreadsheetApp.create(CONFIG.title + '（回答）');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  // 回答が来たらメール通知
  ScriptApp.newTrigger('notifyOnSubmit').forForm(form).onFormSubmit().create();

  Logger.log('回答用URL（LPに貼るURL）: ' + form.getPublishedUrl());
  Logger.log('短縮URL: ' + form.shortenFormUrl(form.getPublishedUrl()));
  Logger.log('編集用URL: ' + form.getEditUrl());
  Logger.log('回答スプレッドシート: ' + ss.getUrl());
}

function notifyOnSubmit(e) {
  const to = CONFIG.notifyEmail || Session.getEffectiveUser().getEmail();
  const lines = e.response.getItemResponses().map(r => {
    const v = r.getResponse();
    return '■ ' + r.getItem().getTitle() + '\n' + (Array.isArray(v) ? v.join(', ') : v);
  });
  MailApp.sendEmail(to, '【個別相談】新しいお申し込みがありました', lines.join('\n\n'));
}
