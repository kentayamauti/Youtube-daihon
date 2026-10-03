// 手紙の PDF（letters.html → Chromium で印刷）と、文面一覧（手紙_全社.md）を作る
// 使い方：node build_letters_pdf.js            … 全員分
//         NAMES=宛名1,宛名2 OUT=spare.html …  指定した宛名だけ（予備の手紙用）
const QR = require('qrcode'); const fs = require('fs');

// 一覧の順番（No. 1〜15）
const list = ['大工後藤株式会社','株式会社公文塗装店','株式会社gomme','株式会社田中でんき','信空自動車株式会社','なごみ建築工房','株式会社ウッドビルド','株式会社ケーエフ工業','株式会社富士スタヂオ','株式会社大貫堂印房','アーネストアカデミー株式会社','音瀬計装有限会社','ほまれの家','グローバルハーツ株式会社','橋本真規'];
const names = process.env.NAMES ? process.env.NAMES.split(',') : list;

// 会社以外の宛先は「御社」を置き換える（個人の方・事業所）
const person = {'橋本真規': '橋本様', 'ほまれの家': '貴事業所'};

const open = '本日は「ゼロから始めるYouTubeチャンネル運用セミナー」にお越しいただき、ありがとうございました。';
const common = [
  '本日お話ししたような戦略を一つずつ積み重ねていけば、御社のお役に立てることがあるかもしれません。',
  'セミナーの中で何か感じていただけたことや、「うちの場合はどうだろう？」と思われたことがあれば、どんな小さなことでもお気軽にご相談ください。個別相談で、御社に合った進め方を一緒に考えさせてください。',
];

// WB工法の2社は同じ文面
const wb = [
  '御社の Instagram とホームページを拝見しました。',
  'WB工法を中心とした発信は、どのような目的で行うかによって、戦略が明確に変わってくると感じています。集客を目的とする場合と、お客様の獲得（工事のご依頼）を目的とする場合とでは戦略が変わり、場合によっては厳しい面もあるかもしれません。発信を続けていくうちに信頼が生まれ、工事のご依頼につながる可能性もあると思いますが、こればかりはやってみないと分からない部分です。',
  'また、実際の現場を撮影し、話し手とカメラマンをつけて、編集まで行う必要があるため、撮影の体制と時間が少し必要になります。手の込んだ作業にはなりますが、YouTube でもいけるのではないかと感じています。',
  'もしご興味があれば、個別相談でお気軽にご相談ください。',
];

// Ykkn さん本人の意見を入れた特別版（キー＝宛名）
const special = {
  '大工後藤株式会社': [
    '御社の Instagram とホームページを拝見しました。',
    '拝見したところ、どのような目的で発信されるかによって、運営のスタイルが変わってくると感じました。',
    '個別相談の場ですので、もし聞きたいことがあれば、何でもお気軽にお聞きいただけましたら幸いです。',
  ],
  '株式会社公文塗装店': [
    '塗装のジャンルを、ひととおり見てみました。',
    '率直に申し上げると、塗装は YouTube とは少し相性が良くないのかもしれない、と感じました。<br>一方で、他の SNS であれば、集客につながる見込みはありそうだと感じています。',
    'ただ、どのくらいのお問い合わせにつながるかは、まだはっきりとは分かりません。もし個別相談の際に、御社がどのようなことを求めているかをお聞かせいただければ、対応できることがあるかもしれません。',
  ],
  '株式会社gomme': [
    '事前に御社のことを調べさせていただいたのですが、どのような事業をされているのかまでは分からず、ジャンルの事前調査ができませんでした。申し訳ございません。',
    ...common,
  ],
  '株式会社田中でんき': [
    '御社の Instagram を拝見しました。こまめに更新されていて、とても良いと思います。一方で、どのような発信をしていけばいいか、迷われているのかなとも感じました。',
    '電気工事は、やるべきことが比較的決まっているジャンルです。目的にもよりますが、その目的が分かれば、ひょっとすると具体的なご提案ができるかもしれません。',
    'ご相談いただく際は、ぜひ目的を具体的にお聞かせください。',
  ],
  '信空自動車株式会社': [
    '御社の Instagram を拝見しました。',
    '率直に申し上げると、AI を露骨に使った発信は、あまり好ましくないのではないかと感じました。',
    '自動車は、同じように発信している事業者さんがたくさんいるジャンルです。お手本にできる発信先が見つかれば、良いご提案ができるかもしれません。',
    '今回どのような目的でセミナーをお聞きいただいたのかをお聞かせいただければ、いろいろと策を打てそうな気がしています。もしご興味があれば、個別相談でお気軽にご相談ください。',
  ],
  'なごみ建築工房': wb,
  '株式会社ウッドビルド': wb,
  '株式会社富士スタヂオ': [
    '御社のホームページを拝見し、あわせて写真撮影のジャンルを俯瞰して見てみました。',
    '率直に申し上げると、写真撮影は YouTube とはあまり相性が良くないのかもしれない、と感じました。YouTube はご年配の方によく見られている媒体だからです。<br>一方で、他の SNS であれば発信の内容を転用しやすく、お客様への広がりも期待できると感じています。',
    'もしご興味があれば、個別相談でもう少し詳しくお話しさせてください。',
  ],
  '株式会社大貫堂印房': [
    '御社の Instagram を拝見し、あわせて「はんこ」のジャンルを俯瞰して見てみました。',
    '私が需要があると感じたのは、外国の方に向けた商品と、お城の印です。<br>こうした内容を発信していけば、ひょっとすると新しいお客様が増えるきっかけになるかもしれない、と感じました。',
    'もしご興味があれば、個別相談でもう少し詳しくお話しさせてください。',
  ],
  '音瀬計装有限会社': [
    '御社の Instagram を拝見しました。',
    'いちご農園では、いちご以外のお野菜も育てていらっしゃるとのことで、そこから辿ってのお客様の集客は見込めるかもしれません。農園での取り組みは、YouTube とも割と相性が良い可能性があると感じています。',
    'ただ、どのような発信が合うかは、御社の目的次第です。もしご興味があれば、個別相談でお気軽にご相談ください。',
  ],
  'ほまれの家': [
    '貴事業所の Instagram とホームページを拝見しました。',
    'どのような目的で、どのようなスタイルで運営していくかによって、発信の形は変わってくると感じています。正直なところ、まだ私の中でイメージがつききっていないため、個別相談で目的などを照らし合わせながら、一緒に考えさせていただければと思います。',
    '障がいのある方の就労支援は、私にとって新しい分野です。実は私も家が近いので、ほまれの家さんが開催されているイベントの会場にも、また伺いたいと思っています。',
  ],
  'グローバルハーツ株式会社': [
    'Instagram と YouTube チャンネルを拝見しました。ご家族で撮影されているのでしょうか。こうしたチャンネルは、私の得意分野でもあります。',
    'そのうえで一番大切なのは、どのような目的で発信されているかだと思っています。もし再生数や登録者数を伸ばしたいのであれば、率直に申し上げると、今のやり方は見直したほうが良いかもしれません。視聴者が求めているのは、発信しているご本人そのものではないことが多いからです。今はご本人が前面に出ている作りなので、そこをどう抑えていくかがポイントになると思います。ご自身が楽しむために作られているのであれば、それも素敵なことですが、YouTube や SNS で伸ばすことを考えると、少し考え方が変わってきます。',
    'また、Instagram は伸びているのに YouTube が伸びていない理由も、ざっくりとですが分かりました。Instagram と YouTube では視聴者がまったく違い、見る方が想像している世界観も違います。そこをぴったり合わせることができれば、伸びていくのではないかと思っています。',
    'もし別の目的がおありでしたら、それもぜひお聞かせください。',
  ],
  '橋本真規': [
    'Instagram を拝見しました。カスタムクレヨンを、どのような形で販売されているのかが気になりました。SNS で今どのような結果が出ているのかも少しお伺いしながら、どういったことをしていけばいいかを考えられたらと思っています。',
    'まだ全体的なリサーチはできていないのですが、私のイメージでは、赤ちゃんと組み合わせるのが良いのではないかと思っています。笑顔の赤ちゃんの「今この瞬間」を残した写真と、その子が大きくなって、そのクレヨンで遊んでいる——そんな未来につながる発信ができたら一番素敵だと思います。',
    'カスタムクレヨンは YouTube とはあまり相性が良くないと思うので、販売につなげるのは他の SNS になると思います。Instagram や TikTok でも大きな再生数までは見込めないかもしれないので、販売をメインに進めていくのが良いと思います。',
    '正直なところ、カスタムクレヨンというジャンルは私もまだ掴めていない部分があり、イメージがつききっていない段階です。もしよろしければ、個別相談で一緒にすり合わせていけたらうれしいです。',
  ],
};

const bodyOf = n => (special[n] || common).map(p => person[n] ? p.replaceAll('御社', person[n]) : p);

(async () => {
  const qr = await QR.toString('https://ykkn-youtube.com/', {type:'svg', margin:0, errorCorrectionLevel:'M'});
  const pages = names.map(n => `<section class="page"><div class="content"><div class="to">${n} 様</div>
<p>${open}</p>${bodyOf(n).map(p => `<p>${p}</p>`).join('')}
<div class="sign">ykkn 山内</div></div>
<div class="box"><div class="info"><div class="t">個別相談のご案内（受講者限定）</div>
<div class="price">特別価格 <b>15,000円</b>（税込）<span class="s">通常 30,000円</span></div>
<div>お申し込み期限：<b>10月10日（土）</b>まで</div><div class="url">ykkn-youtube.com</div></div>
<div class="qr">${qr}<div class="cap">読み取ってお申し込み</div></div></div></section>`).join('');
  const html = `<!doctype html><html lang="ja"><head><meta charset="utf-8">
<link rel="stylesheet" href="node_modules/@fontsource/noto-serif-jp/400.css"><link rel="stylesheet" href="node_modules/@fontsource/noto-serif-jp/700.css">
<style>@page{size:A5;margin:0}*{box-sizing:border-box}body{margin:0;font-family:'Noto Serif JP',serif;color:#222;font-size:10.5pt;line-height:1.95}
.page{width:148mm;height:210mm;padding:20mm 16mm 14mm;page-break-after:always;display:flex;flex-direction:column;overflow:hidden}
.content{flex:1;min-height:0;overflow:hidden}
.to{font-size:13pt;font-weight:700;border-bottom:1px solid #999;padding-bottom:2mm;margin-bottom:8mm;display:inline-block}
p{margin:0 0 4.5mm;text-align:justify}.sign{text-align:right;margin-top:8mm;font-size:11pt}
.box{margin-top:5mm;border:1px solid #bbb;border-radius:2mm;padding:4mm 5mm;display:flex;gap:5mm;align-items:center;font-size:9pt;line-height:1.7}
.info{flex:1}.t{font-weight:700;font-size:10pt;margin-bottom:1mm}.price b{font-size:12pt}.s{color:#777;margin-left:2mm;text-decoration:line-through}.url{margin-top:1mm;letter-spacing:.03em}
.qr{width:30mm;text-align:center}.qr svg{width:24mm;height:24mm}.cap{font-size:6.5pt;color:#555;line-height:1.3;margin-top:1mm}</style>
<script>
// 長い手紙は、1枚に収まるまで本文の文字を少しずつ小さくする
document.fonts.ready.then(() => {
  for (const c of document.querySelectorAll('.content')) {
    let size = 10.5, gap = 4.5;
    while (c.scrollHeight > c.clientHeight && size > 8.5) {
      size -= 0.25; gap = Math.max(2.5, gap - 0.2);
      c.style.fontSize = size + 'pt'; c.style.lineHeight = size < 9.75 ? '1.8' : '1.95';
      c.querySelectorAll('p').forEach(p => p.style.marginBottom = gap + 'mm');
    }
    if (c.scrollHeight > c.clientHeight) document.title = 'OVERFLOW';
  }
});
</script></head><body>${pages}</body></html>`;
  fs.writeFileSync(__dirname + '/' + (process.env.OUT || 'letters.html'), html);

  if (process.env.NAMES) return;
  // 文面一覧（Markdown）も同じデータから作る
  const strip = p => p.replaceAll('<br>', '\n');
  const md = ['# 参加企業への手紙（全' + list.length + '件）', '',
    '> このファイルは `build_letters_pdf.js` から自動で作っています。文面を直すときはスクリプト側を直してください。', '',
    '- 想定：セミナー当日（10/5）にお渡し。印刷して、最後の名前だけ手書き',
    '- 方針：手紙に書く意見は **ykkn 山内さんが感じたことだけ**。こちらで調べた内容や独自の提案は入れない',
    '- 特別版：' + list.filter(n => special[n]).length + '件／共通文面：' + list.filter(n => !special[n]).map(n => n + ' 様').join('、'),
    '- 個別相談のご案内（15,000円・10/10まで・QRコード）と署名「ykkn 山内」は全員共通', '',
    ...list.flatMap((n, i) => ['---', '', `## ${i + 1}. ${n} 様${special[n] ? '' : '（共通文面）'}`, '', open, '', ...bodyOf(n).flatMap(p => [strip(p), '']), 'ykkn 山内', '']),
    '---', '', '※ 橋本建設株式会社は 9/30 の一覧から外れた（キャンセルかどうか確認中）。参加の場合に備えて、共通文面の手紙を `手紙_予備_橋本建設.pdf` として別に用意', ''];
  fs.writeFileSync(__dirname + '/手紙_全社.md', md.join('\n'));
})();
