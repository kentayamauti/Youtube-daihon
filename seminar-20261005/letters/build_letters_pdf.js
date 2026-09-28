const QR = require('qrcode'); const fs = require('fs');
const names = ['大工後藤株式会社','橋本建設株式会社','株式会社公文塗装店','株式会社gomme','株式会社田中でんき','信空自動車株式会社','なごみ建築工房','株式会社ウッドビルド','株式会社ケーエフ工業','株式会社富士スタヂオ','株式会社大貫堂印房','アーネストアカデミー株式会社','音瀬計装有限会社'];
const common = ['本日お話ししたような戦略を一つずつ積み重ねていけば、御社のお役に立てることがあるかもしれません。','もしご興味があれば、個別相談で御社に合った進め方を一緒に考えさせてください。'];
const special = {'株式会社富士スタヂオ': ['御社のホームページを拝見し、あわせて写真撮影のジャンルを俯瞰して見てみました。','率直に申し上げると、写真撮影は YouTube とはあまり相性が良くないのかもしれない、と感じました。YouTube はご年配の方によく見られている媒体だからです。<br>一方で、他の SNS であれば発信の内容を転用しやすく、お客様への広がりも期待できると感じています。','もしご興味があれば、個別相談でもう少し詳しくお話しさせてください。'],
'株式会社大貫堂印房': ['御社の Instagram を拝見し、あわせて「はんこ」のジャンルを俯瞰して見てみました。','私が需要があると感じたのは、外国の方に向けた商品と、お城の印です。<br>こうした内容を発信していけば、ひょっとすると新しいお客様が増えるきっかけになるかもしれない、と感じました。','もしご興味があれば、個別相談でもう少し詳しくお話しさせてください。']};
(async () => {
  const qr = await QR.toString('https://ykkn-youtube.com/', {type:'svg', margin:0, errorCorrectionLevel:'M'});
  const pages = names.map(n => {
    const body = (special[n] || common).map(p => `<p>${p}</p>`).join('');
    return `<section class="page"><div class="to">${n} 様</div>
<p>本日は「ゼロから始めるYouTubeチャンネル運用セミナー」にお越しいただき、ありがとうございました。</p>${body}
<div class="sign">ykkn 山内</div>
<div class="box"><div class="info"><div class="t">個別相談のご案内（受講者限定）</div>
<div class="price">特別価格 <b>15,000円</b>（税込）<span class="s">通常 30,000円</span></div>
<div>お申し込み期限：<b>10月10日（土）</b>まで</div><div class="url">ykkn-youtube.com</div></div>
<div class="qr">${qr}<div class="cap">読み取ってお申し込み</div></div></div></section>`;
  }).join('');
  const html = `<!doctype html><html lang="ja"><head><meta charset="utf-8">
<link rel="stylesheet" href="node_modules/@fontsource/noto-serif-jp/400.css"><link rel="stylesheet" href="node_modules/@fontsource/noto-serif-jp/700.css">
<style>@page{size:A5;margin:0}*{box-sizing:border-box}body{margin:0;font-family:'Noto Serif JP',serif;color:#222;font-size:10.5pt;line-height:1.95}
.page{width:148mm;height:210mm;padding:20mm 16mm 14mm;page-break-after:always;position:relative}
.to{font-size:13pt;font-weight:700;border-bottom:1px solid #999;padding-bottom:2mm;margin-bottom:8mm;display:inline-block}
p{margin:0 0 4.5mm;text-align:justify}.sign{text-align:right;margin-top:8mm;font-size:11pt}
.box{position:absolute;left:16mm;right:16mm;bottom:14mm;border:1px solid #bbb;border-radius:2mm;padding:4mm 5mm;display:flex;gap:5mm;align-items:center;font-size:9pt;line-height:1.7}
.info{flex:1}.t{font-weight:700;font-size:10pt;margin-bottom:1mm}.price b{font-size:12pt}.s{color:#777;margin-left:2mm;text-decoration:line-through}.url{margin-top:1mm;letter-spacing:.03em}
.qr{width:30mm;text-align:center}.qr svg{width:24mm;height:24mm}.cap{font-size:6.5pt;color:#555;line-height:1.3;margin-top:1mm}</style></head><body>${pages}</body></html>`;
  fs.writeFileSync(__dirname + '/letters.html', html);
})();
