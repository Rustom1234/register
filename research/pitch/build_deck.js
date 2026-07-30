// Wayside — Kevin Xu Innovation Challenge pitch deck (Equitech template sections)
const path = require("path");
const pptxgen = require("pptxgenjs");
const ASSETS = path.join(__dirname, "assets");

// Wayside's own validated identity: dark ops sandwich + category colors
const INK = "16181D", MUT = "52514E", FAINT = "898781";
const PAGE_D = "0D0D0D", SURF_D = "12141A", LINE_D = "2A2E38";
const GOOD = "0CA30C", MED = "3987E5", FOOD = "D95926", SHEL = "199E70";
const WARN = "B7791F", CRIT = "D03B3B", CARD = "F4F5F7";

const p = new pptxgen();
p.layout = "LAYOUT_WIDE";                       // 13.33 x 7.5
p.theme = { headFontFace: "Arial", bodyFontFace: "Arial" };

const W = 13.33, H = 7.5, M = 0.55;

function dot(s, x, y, color, d = 0.14) {
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color } });
}
function title(s, txt, color = INK) {
  s.addText(txt, { x: M, y: 0.42, w: W - 2 * M, h: 0.75, fontSize: 34, bold: true,
    color, fontFace: "Arial", margin: 0 });
}
function kicker(s, txt, color = FAINT) {
  s.addText(txt.toUpperCase(), { x: M, y: 0.16, w: W - 2 * M, h: 0.3, fontSize: 11,
    color, charSpacing: 3, fontFace: "Arial", margin: 0 });
}

// ---------------------------------------------------------------- 1 TITLE
let s = p.addSlide();
s.background = { color: PAGE_D };
s.addText("📍", { x: M, y: 1.55, w: 1.2, h: 1.0, fontSize: 44, margin: 0 });
s.addText([
  { text: "WAYSIDE", options: { fontSize: 60, bold: true, color: "FFFFFF", charSpacing: 6 } },
  { text: "   see it, send word.", options: { fontSize: 22, color: FAINT } },
], { x: M, y: 2.3, w: 11.5, h: 1.25, margin: 0 });
s.addText("One WhatsApp number that turns anyone who stops on the street\ninto the start of a real aid response.",
  { x: M, y: 3.62, w: 10.6, h: 1.0, fontSize: 20, color: "C3C2B7", margin: 0, lineSpacing: 27 });
[["No cameras", MED], ["No database of the poor", SHEL], ["Working demo · 111 tests", GOOD]].forEach(([t, c], i) => {
  const x = M + i * 3.42;
  s.addShape("roundRect", { x, y: 4.85, w: 3.2, h: 0.52, rectRadius: 0.26,
    fill: { color: SURF_D }, line: { color: LINE_D, width: 1 } });
  dot(s, x + 0.22, y = 5.04, c, 0.13);
  s.addText(t, { x: x + 0.44, y: 4.85, w: 2.72, h: 0.52, fontSize: 12.5, color: "E8E6DF",
    valign: "middle", margin: 0 });
});
s.addText("Kevin Xu Innovation Challenge  ·  Rustom Dubash  ·  Equitech alum",
  { x: M, y: 6.65, w: 10.5, h: 0.4, fontSize: 13, color: FAINT, margin: 0 });

// -------------------------------------------------------------- 2 PROBLEM
s = p.addSlide();
s.background = { color: "FFFFFF" };
kicker(s, "The problem");
title(s, "Everyone walks past — because nothing works to do");
s.addText([
  { text: "You see a man under a flyover, foot wrapped in a soaked bandage. You stop. And then… what? ", options: { bold: true } },
  { text: "112 is for emergencies. Helplines go to voicemail. Giving cash can now mean a police case for him. So the two minutes of caring evaporate — every day, in every city.\n\n", options: {} },
  { text: "Who it affects. ", options: { bold: true } },
  { text: "1.7 million+ people live on India's streets; injuries, hunger and exposure kill quietly every winter and monsoon. And it affects every passer-by who wanted to act and had no channel.\n\n", options: {} },
  { text: "Why care now. ", options: { bold: true } },
  { text: "The two dominant answers both fail: surveillance and black holes.", options: {} },
], { x: M, y: 1.45, w: 6.7, h: 4.6, fontSize: 15, color: INK, margin: 0, lineSpacing: 21 });
const stats = [
  ["10–15%", "accuracy of San Jose's camera-AI homeless detection — shut down in 2025", CRIT],
  ["23% / 5%", "of UK StreetLink reports led to finding / housing the person — witnesses stop reporting into silence", WARN],
  ["₹0", "reaches the person in the moment a witness cares, today", MUT],
];
stats.forEach(([n, t, c], i) => {
  const y0 = 1.45 + i * 1.62;
  s.addShape("roundRect", { x: 7.8, y: y0, w: 5.0, h: 1.42, rectRadius: 0.09,
    fill: { color: CARD } });
  s.addText(n, { x: 8.1, y: y0 + 0.12, w: 4.4, h: 0.62, fontSize: 30, bold: true, color: c, margin: 0 });
  s.addText(t, { x: 8.1, y: y0 + 0.72, w: 4.5, h: 0.62, fontSize: 11.5, color: MUT, margin: 0 });
});
s.addText("The gap isn't compassion. It's a channel that answers.",
  { x: M, y: 6.55, w: 8.5, h: 0.45, fontSize: 15, italic: true, color: MUT, margin: 0 });

// ---------------------------------------------------------- 3 OPPORTUNITY
s = p.addSlide();
s.background = { color: "FFFFFF" };
kicker(s, "The opportunity");
title(s, "Why now, why me");
const rows = [
  [MED, "Everyone already has the app", "500M+ Indians use WhatsApp daily. Reporting must cost one message — now it can."],
  [SHEL, "AI can finally take the report", "LLMs reliably structure Hinglish/Hindi/English into location + need + urgency for pennies. Impossible two years ago."],
  [FOOD, "Dispatch patterns are proven", "GoodSAM showed parallel offers + first-accept gets a yes in ~a minute. India Post's DIGIPIN gives every pavement a 4 m address."],
  [GOOD, "Privacy is now the moat", "DPDP Act (2023) punishes hoarding personal data. A system designed to never build the dangerous database wins partners and regulators."],
];
rows.forEach(([c, h, b], i) => {
  const y0 = 1.5 + i * 1.06;
  dot(s, M + 0.02, y0 + 0.09, c, 0.2);
  s.addText(h, { x: M + 0.42, y: y0, w: 6.9, h: 0.36, fontSize: 15.5, bold: true, color: INK, margin: 0 });
  s.addText(b, { x: M + 0.42, y: y0 + 0.34, w: 7.0, h: 0.62, fontSize: 12.5, color: MUT, margin: 0 });
});
s.addShape("roundRect", { x: 8.2, y: 1.5, w: 4.58, h: 4.25, rectRadius: 0.1, fill: { color: PAGE_D } });
s.addText("THE EDGE", { x: 8.55, y: 1.8, w: 3.9, h: 0.3, fontSize: 11, color: FAINT, charSpacing: 3, margin: 0 });
s.addText("“The sensor isn't a camera.\nIt's a person who already stopped.”",
  { x: 8.55, y: 2.2, w: 3.95, h: 1.5, fontSize: 19, bold: true, color: "FFFFFF", margin: 0, lineSpacing: 25 });
s.addText("Equitech alum · built the working system solo — pipeline, control room, responder app, 111 tests — before asking for a rupee. Every design choice cites evidence from systems that failed before it.",
  { x: 8.55, y: 3.85, w: 3.95, h: 1.6, fontSize: 12.5, color: "C3C2B7", margin: 0, lineSpacing: 17 });
s.addText("Nothing here requires new behaviour — only a number worth saving.",
  { x: M, y: 6.55, w: 9.0, h: 0.45, fontSize: 15, italic: true, color: MUT, margin: 0 });

// ------------------------------------------------------------- 4 SOLUTION
s = p.addSlide();
s.background = { color: "FFFFFF" };
kicker(s, "The solution");
title(s, "One message, answered — end to end");
const steps = [
  ["1", "Witness sends one WhatsApp", "text, voice note or photo — English, Hinglish or हिंदी", MED],
  ["2", "Deterministic 112 gate", "real emergencies get a fixed redirect before any AI speaks", CRIT],
  ["3", "AI agent structures the report", "location (DIGIPIN), need, urgency → medical / food / shelter kit order", SHEL],
  ["4", "Parallel offers, first accept wins", "nearest trusted NGO responders get the job like a ride request", FOOD],
  ["5", "Kit delivered, outcome recorded", "served · escalated to clinical · not found · declined — respected", GOOD],
  ["6", "The witness is told how it ended", "“Meena reached him, help was given. Thank you.”", MED],
];
steps.forEach(([n, h, b, c], i) => {
  const col = i % 3, row = Math.floor(i / 3);
  const x = M + col * 4.18, y0 = 1.5 + row * 2.06;
  s.addShape("roundRect", { x, y: y0, w: 3.92, h: 1.86, rectRadius: 0.1, fill: { color: CARD } });
  s.addShape("ellipse", { x: x + 0.22, y: y0 + 0.22, w: 0.46, h: 0.46, fill: { color: c } });
  s.addText(n, { x: x + 0.22, y: y0 + 0.22, w: 0.46, h: 0.46, fontSize: 16, bold: true,
    color: "FFFFFF", align: "center", valign: "middle", margin: 0 });
  s.addText(h, { x: x + 0.82, y: y0 + 0.18, w: 3.0, h: 0.62, fontSize: 13.5, bold: true, color: INK, margin: 0 });
  s.addText(b, { x: x + 0.24, y: y0 + 0.88, w: 3.5, h: 0.88, fontSize: 11.5, color: MUT, margin: 0 });
});
s.addText([
  { text: "Value hypothesis: ", options: { bold: true, color: INK } },
  { text: "closing the loop turns one-time witnesses into repeat reporters — gratitude is the growth engine. Delivered as a service: a WhatsApp line for the public (nothing to install), a control room + responder web app for the NGO.", options: { color: MUT } },
], { x: M, y: 5.75, w: 12.2, h: 0.85, fontSize: 13.5, margin: 0, lineSpacing: 18 });

// ----------------------------------------------------------------- 5 DEMO
s = p.addSlide();
s.background = { color: "FFFFFF" };
kicker(s, "The demo — it runs today");
title(s, "Not a mockup: 111 tests, three surfaces, one loop");
s.addImage({ path: `${ASSETS}/room.png`, x: M, y: 1.55, w: 7.9, h: 4.7, rounding: true });
s.addImage({ path: `${ASSETS}/resp-offer.png`, x: 8.75, y: 1.55, w: 1.95, h: 4.18, rounding: true });
s.addText([
  { text: "Control room\n", options: { bold: true, fontSize: 12.5, color: INK } },
  { text: "live map, dispatch waves, kit stock, kill-criteria dashboard\n\n", options: { fontSize: 11, color: MUT } },
  { text: "Responder app\n", options: { bold: true, fontSize: 12.5, color: INK } },
  { text: "offer ping → checklist → outcome, on any phone\n\n", options: { fontSize: 11, color: MUT } },
  { text: "Witness phone\n", options: { bold: true, fontSize: 12.5, color: INK } },
  { text: "trilingual chat, photo picker, live progress, “still there?” check", options: { fontSize: 11, color: MUT } },
], { x: 10.9, y: 1.55, w: 1.95, h: 4.4, margin: 0 });
s.addText("Recorded 2:22 walkthrough + interactive session replay available · runs offline on a laptop with zero API keys",
  { x: M, y: 6.5, w: 12.2, h: 0.4, fontSize: 12.5, italic: true, color: MUT, margin: 0 });

// -------------------------------------------------------------- 6 CUSTOMER
s = p.addSlide();
s.background = { color: "FFFFFF" };
kicker(s, "The customer — who pays");
title(s, "NGOs and CSR budgets buying verified outcomes");
const cust = [
  ["Who buys", "NGO street-outreach programs and the CSR funders behind them (India mandates 2% of corporate profit to CSR), plus municipal shelter boards.", MED],
  ["Pain solved", "Outreach teams find people too late and blind; donors get activity reports, not verified outcomes; data practices now carry DPDP legal risk.", FOOD],
  ["What they get", "A per-zone service: verified need → delivered kit → coded outcome, with provenance-tagged records and privacy by architecture — audit-ready.", SHEL],
  ["First customer", "One Delhi NGO, one pilot zone (Nizamuddin). Reached through the Equitech network and an existing Goonj relationship — pitch is a working demo, not a proposal.", GOOD],
];
cust.forEach(([h, b, c], i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = M + col * 6.25, y0 = 1.55 + row * 2.4;
  s.addShape("roundRect", { x, y: y0, w: 5.95, h: 2.2, rectRadius: 0.1, fill: { color: CARD } });
  dot(s, x + 0.28, y0 + 0.32, c, 0.18);
  s.addText(h, { x: x + 0.6, y: y0 + 0.2, w: 5.0, h: 0.4, fontSize: 15, bold: true, color: INK, margin: 0 });
  s.addText(b, { x: x + 0.3, y: y0 + 0.68, w: 5.35, h: 1.42, fontSize: 12.5, color: MUT, margin: 0, lineSpacing: 17 });
});
s.addText("Unit economics to defend in the pilot: ~₹300 kit + delivery ≈ ₹430 per person served — kill line at ₹900.",
  { x: M, y: 6.55, w: 12.2, h: 0.4, fontSize: 13, italic: true, color: MUT, margin: 0 });

// ----------------------------------------------------------------- 7 USERS
s = p.addSlide();
s.background = { color: "FFFFFF" };
kicker(s, "The users");
title(s, "Three users — and one deliberate non-user");
const users = [
  ["The witness", "any passer-by · uses only WhatsApp, nothing to install · gets progress + closure, so they report again", MED],
  ["The responder", "vetted NGO field worker · gets the offer ping with kit, distance, DIGIPIN · one tap records the outcome", SHEL],
  ["The coordinator", "NGO staff · watches the control room · handles the edge cases the system refuses to guess at", FOOD],
];
users.forEach(([h, b, c], i) => {
  const x = M + i * 4.18;
  s.addShape("roundRect", { x, y: 1.55, w: 3.92, h: 2.5, rectRadius: 0.1, fill: { color: CARD } });
  dot(s, x + 0.26, y = 1.88, c, 0.18);
  s.addText(h, { x: x + 0.56, y: 1.75, w: 3.1, h: 0.4, fontSize: 15.5, bold: true, color: INK, margin: 0 });
  s.addText(b, { x: x + 0.28, y: 2.25, w: 3.4, h: 1.66, fontSize: 12.5, color: MUT, margin: 0, lineSpacing: 17 });
});
s.addShape("roundRect", { x: M, y: 4.45, w: 12.23, h: 1.85, rectRadius: 0.1, fill: { color: PAGE_D } });
s.addText([
  { text: "The person in need is served — never enrolled.  ", options: { bold: true, color: "FFFFFF", fontSize: 16 } },
  { text: "No name, no photo of a face, no profile is ever stored. Exact locations are wiped once a case closes; after 90 days only coarse heat-cells remain. In a country that still criminalises begging, the strongest protection is that the dangerous database never exists.", options: { color: "C3C2B7", fontSize: 13 } },
], { x: M + 0.35, y: 4.7, w: 11.5, h: 1.4, margin: 0, lineSpacing: 19 });
s.addText("Dignity is a design constraint, not a caption.",
  { x: M, y: 6.6, w: 9.0, h: 0.4, fontSize: 14, italic: true, color: MUT, margin: 0 });

// --------------------------------------------------------------- 8 ROADMAP
s = p.addSlide();
s.background = { color: "FFFFFF" };
kicker(s, "Roadmap");
title(s, "Three months to truth, twelve to scale — or an honest stop");
s.addText("NEXT 3 MONTHS — ONE ZONE, REAL PEOPLE", { x: M, y: 1.5, w: 6.0, h: 0.32, fontSize: 12.5, bold: true, color: MED, charSpacing: 1, margin: 0 });
s.addText([
  { text: "Real WhatsApp number live (transport is built — onboarding is configuration)", options: { bullet: true, breakLine: true } },
  { text: "One NGO partner, 6–10 rostered responders, Nizamuddin pilot zone", options: { bullet: true, breakLine: true } },
  { text: "Hindi/Hinglish voice-note speech-to-text bake-off (Sarvam vs Whisper)", options: { bullet: true, breakLine: true } },
  { text: "8-week pilot measured against pre-registered kill criteria", options: { bullet: true } },
], { x: M, y: 1.9, w: 6.1, h: 2.3, fontSize: 13, color: INK, margin: 0, paraSpaceAfter: 8 });
s.addText("BY 12 MONTHS — IF THE NUMBERS HOLD", { x: 7.15, y: 1.5, w: 6.0, h: 0.32, fontSize: 12.5, bold: true, color: SHEL, charSpacing: 1, margin: 0 });
s.addText([
  { text: "Three zones, two partners — onboarding a partner is config + a playbook", options: { bullet: true, breakLine: true } },
  { text: "Voice-first reporting; DPDP audit + published transparency report", options: { bullet: true, breakLine: true } },
  { text: "Public dashboard of outcomes — the same one the funders see", options: { bullet: true } },
], { x: 7.15, y: 1.9, w: 5.7, h: 2.2, fontSize: 13, color: INK, margin: 0, paraSpaceAfter: 8 });
s.addShape("roundRect", { x: M, y: 4.35, w: 12.23, h: 1.55, rectRadius: 0.1, fill: { color: CARD } });
s.addText([
  { text: "Pre-registered kill criteria — public before the pilot starts:  ", options: { bold: true, color: INK } },
  { text: "offer acceptance ≥ 50% · verified-need rate ≥ 40% · cost per person served ≤ ₹900 · backlog never outgrows capacity. If Wayside stops earning its numbers, its own dashboard says so — and we publish that and stop.", options: { color: MUT } },
], { x: M + 0.3, y: 4.55, w: 11.6, h: 1.2, fontSize: 13, margin: 0, lineSpacing: 18 });
s.addText([
  { text: "Resources needed: ", options: { bold: true, color: INK } },
  { text: "pilot grant (kits, responder stipends, WhatsApp + AI costs, DPIA/legal review) · partner introductions · mentorship on NGO ops.", options: { color: MUT } },
], { x: M, y: 6.25, w: 12.2, h: 0.6, fontSize: 13.5, margin: 0 });

// ----------------------------------------------------------------- 9 CLOSE
s = p.addSlide();
s.background = { color: PAGE_D };
s.addText("📍", { x: M, y: 1.5, w: 1.0, h: 0.9, fontSize: 40, margin: 0 });
s.addText("No cameras.\nNo database of the poor.\nNo one left by the wayside.",
  { x: M, y: 2.4, w: 11.5, h: 2.6, fontSize: 38, bold: true, color: "FFFFFF", margin: 0, lineSpacing: 50 });
s.addText("The ask: pilot funding for one zone · introductions to Delhi street-outreach NGOs · a mentor who has run field ops.",
  { x: M, y: 5.35, w: 11.6, h: 0.5, fontSize: 16, color: "C3C2B7", margin: 0 });
s.addText("Rustom Dubash · rustommdubash@gmail.com · working demo, 2:22 video and full research corpus on request",
  { x: M, y: 6.6, w: 12.0, h: 0.4, fontSize: 12.5, color: FAINT, margin: 0 });

p.writeFile({ fileName: path.join(__dirname, "wayside-kxic-pitch.pptx") })
  .then(() => console.log("written"));
