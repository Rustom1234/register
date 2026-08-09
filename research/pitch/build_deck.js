// Wayside — Kevin Xu Innovation Challenge pitch deck (Equitech template sections)
// Dark-throughout edition, matching the long-form web pitch. Fonts kept to
// Georgia / Arial / Courier New — universally installed, no embedding needed.
const path = require("path");
const pptxgen = require("pptxgenjs");
const ASSETS = path.join(__dirname, "assets");

const PAGE = "0B0C10", SURF = "14161C", LINE = "2A2E38";
const INK = "ECE9E2", DIM = "C8C5BD", FAINT = "8B8A82";
const LAMP = "F2A93B", LAMP_DIM = "B9822F";
const MED = "3987E5", FOOD = "D95926", SHEL = "199E70", GOOD = "0CA30C", CRIT = "E0625D";

const SERIF = "Georgia", SANS = "Arial", MONO = "Courier New";

const p = new pptxgen();
p.layout = "LAYOUT_WIDE";                       // 13.33 x 7.5
p.theme = { headFontFace: SANS, bodyFontFace: SANS };

const W = 13.33, H = 7.5, M = 0.55;

function bg(s) { s.background = { color: PAGE }; }
function dot(s, x, y, color, d = 0.13) {
  s.addShape("ellipse", { x, y, w: d, h: d, fill: { color } });
}
function kicker(s, txt, x = M, y = 0.55) {
  s.addText(txt.toUpperCase(), { x, y, w: W - 2 * M, h: 0.3, fontSize: 11,
    color: LAMP, charSpacing: 3, fontFace: MONO, margin: 0 });
}
function title(s, txt, x = M, y = 0.92, w = W - 2 * M) {
  s.addText(txt, { x, y, w, h: 1.05, fontSize: 32, bold: true,
    color: INK, fontFace: SERIF, margin: 0, lineSpacing: 36 });
}
function lede(s, txt, x, y, w, size = 14.5) {
  s.addText(txt, { x, y, w, h: 0.9, fontSize: size, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 20 });
}
function aside(s, txt, x, y, w) {
  s.addShape("line", { x, y: y - 0.16, w, h: 0, line: { color: LINE, width: 0.75 } });
  s.addText(txt, { x, y, w, h: 0.5, fontSize: 14.5, italic: true, color: LAMP, fontFace: SERIF, margin: 0 });
}
function card(s, x, y, w, h, r = 0.09) {
  s.addShape("roundRect", { x, y, w, h, rectRadius: r, fill: { color: SURF }, line: { color: LINE, width: 1 } });
}
function footer(s, n) {
  s.addText(`WAYSIDE — ${n}/13`, { x: W - M - 2.3, y: H - 0.36, w: 2.3, h: 0.26, fontSize: 8.5, color: LINE, fontFace: MONO, charSpacing: 1, align: "right", margin: 0 });
}

// ---------------------------------------------------------------- 1 TITLE
let s = p.addSlide(); bg(s);
s.addText("KEVIN XU INNOVATION CHALLENGE — EQUITECH ALUMNI TRACK",
  { x: M, y: 1.5, w: 11.5, h: 0.3, fontSize: 11.5, color: LAMP, charSpacing: 3, fontFace: MONO, margin: 0 });
s.addText([
  { text: "Wayside", options: { fontSize: 74, bold: true, color: INK } },
  { text: ".", options: { fontSize: 74, bold: true, color: LAMP } },
], { x: M, y: 1.95, w: 11.5, h: 1.6, fontFace: SERIF, margin: 0 });
s.addText("see it, send word.", { x: M, y: 3.55, w: 9, h: 0.55, fontSize: 22, italic: true, color: LAMP, fontFace: SERIF, margin: 0 });
s.addText("One WhatsApp number turns anyone who stops on the street into the start of a real aid response — no app to download, no face on file, no database of the people it serves. Just a message that gets answered.",
  { x: M, y: 4.25, w: 9.6, h: 1.0, fontSize: 15.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 22 });
[["No cameras", MED], ["No database of the poor", SHEL], ["Working demo · 224 tests", GOOD]].forEach(([t, c], i) => {
  const x = M + i * 3.42, y0 = 5.55;
  s.addShape("roundRect", { x, y: y0, w: 3.2, h: 0.52, rectRadius: 0.26, fill: { color: SURF }, line: { color: LINE, width: 1 } });
  dot(s, x + 0.22, y0 + 0.19, c, 0.13);
  s.addText(t, { x: x + 0.44, y: y0, w: 2.72, h: 0.52, fontSize: 12, color: INK, fontFace: SANS, valign: "middle", margin: 0 });
});
s.addText("Kevin Xu Innovation Challenge  ·  Rustom Dubash  ·  Equitech alum",
  { x: M, y: 6.7, w: 10.5, h: 0.35, fontSize: 12.5, color: FAINT, fontFace: MONO, margin: 0 });

// -------------------------------------------------------- 2 PROBLEM: STORY
s = p.addSlide(); bg(s);
kicker(s, "01 — The problem");
title(s, "Everyone walks past, because there's nothing to do");
s.addText([
  { text: "You see a man under a flyover. His foot is wrapped in a bandage that's gone through and darkened again. You stop — for a second, you actually stop. And then: what?\n\n", options: {} },
  { text: "112 is for emergencies, and a soaked bandage doesn't sound like one on the phone. The helpline numbers people forward on WhatsApp ring out or go to voicemail. Handing over cash can, in some cities, turn into a police matter for ", options: {} },
  { text: "him", options: { italic: true } },
  { text: ", not you.\n\n", options: {} },
  { text: "So you do the only thing left: you keep walking. The two minutes you were willing to give evaporate — the same way they do for the next person, every day, in every city.", options: {} },
], { x: M, y: 2.15, w: 8.0, h: 3.5, fontSize: 15.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 22 });
card(s, 8.55, 2.15, 4.23, 4.1);
s.addText("WHO IT AFFECTS", { x: 8.85, y: 2.42, w: 3.7, h: 0.3, fontSize: 10.5, color: LAMP, charSpacing: 2, fontFace: MONO, margin: 0 });
s.addText("More than 1.7 million people sleep on India's streets. Injuries go septic, hunger and exposure do their quiet work every winter and monsoon — not dramatically, just steadily, unwitnessed by anyone with the power to act.",
  { x: 8.85, y: 2.8, w: 3.65, h: 1.7, fontSize: 12.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 18 });
s.addText("WHY CARE NOW", { x: 8.85, y: 4.6, w: 3.7, h: 0.3, fontSize: 10.5, color: LAMP, charSpacing: 2, fontFace: MONO, margin: 0 });
s.addText("It isn't only their problem — it's the passer-by's too. The one who wanted to do something real, and found no channel built for the two minutes they had.",
  { x: 8.85, y: 4.98, w: 3.65, h: 1.2, fontSize: 12.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 18 });
aside(s, "The gap isn't compassion. It's a channel that answers.", M, 6.85, 9.5);
footer(s, 2);

// ------------------------------------------------------ 3 PROBLEM: NUMBERS
s = p.addSlide(); bg(s);
kicker(s, "01 — The problem, in numbers");
title(s, "Two answers already exist. Both fail.");
lede(s, "One end of the spectrum watches too much. The other answers too little.", M, 1.95, 10.5, 15);
const stats = [
  ["10–15%", "accuracy of San Jose's camera-AI homeless detection system — shut down in 2025", CRIT],
  ["23% / 5%", "of UK StreetLink reports led to finding / housing the person — witnesses stop reporting into silence", LAMP],
  ["₹0", "reaches the person in the moment a witness cares, today", FAINT],
];
stats.forEach(([n, t, c], i) => {
  const x = M + i * 4.13;
  card(s, x, 2.8, 3.9, 3.4, 0.12);
  s.addText(n, { x: x + 0.35, y: 3.15, w: 3.2, h: 1.15, fontSize: 46, bold: true, color: c, fontFace: MONO, margin: 0 });
  s.addText(t, { x: x + 0.35, y: 4.4, w: 3.25, h: 1.55, fontSize: 13, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 18 });
});
aside(s, "The gap isn't compassion. It's a channel that answers.", M, 6.85, 9.5);
footer(s, 3);

// ------------------------------------------------------------ 4 OPPORTUNITY
s = p.addSlide(); bg(s);
kicker(s, "02 — Why now");
title(s, "Why now, why me");
const reasons = [
  ["DISTRIBUTION", "Everyone already has the app", "500 million-plus Indians open WhatsApp every day. Reporting can cost exactly one message — the channel they already use is the channel that answers."],
  ["TECHNOLOGY", "AI can finally take the report", "LLMs now reliably turn a panicked, code-switched voice note — Hindi, English, Hinglish — into a structured report. Two years ago this took a call centre; today it's a pipeline, for pennies a message."],
  ["OPERATIONS", "Dispatch patterns are proven", "GoodSAM showed that offering a case to several nearby responders at once, first-to-accept, gets a yes inside a minute. India Post's DIGIPIN now gives every stretch of pavement its own short address."],
  ["REGULATION", "Privacy is now the moat", "India's DPDP Act makes hoarding personal data a liability, not an asset. A system built to never collect a name, a face, or an address is the version regulators and NGOs trust first."],
];
reasons.forEach(([tag, h, b], i) => {
  const y0 = 2.05 + i * 1.18;
  s.addText(tag, { x: M, y: y0 + 0.03, w: 1.7, h: 0.3, fontSize: 10, color: LAMP, charSpacing: 1.5, fontFace: MONO, margin: 0 });
  s.addText(h, { x: M + 1.85, y: y0, w: 4.7, h: 0.36, fontSize: 14.5, bold: true, color: INK, fontFace: SANS, margin: 0 });
  s.addText(b, { x: M + 1.85, y: y0 + 0.36, w: 4.75, h: 0.78, fontSize: 11.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 15.5 });
});
card(s, 7.15, 2.0, 5.63, 4.55, 0.12);
s.addText("THE EDGE", { x: 7.5, y: 2.3, w: 5, h: 0.3, fontSize: 10.5, color: LAMP, charSpacing: 2, fontFace: MONO, margin: 0 });
s.addText("“The sensor isn't a camera.\nIt's a person who already stopped.”",
  { x: 7.5, y: 2.72, w: 4.95, h: 1.55, fontSize: 21, italic: true, color: INK, fontFace: SERIF, margin: 0, lineSpacing: 27 });
s.addText("Equitech alum. Built the whole system solo — intake pipeline, control room, responder app, 224 automated tests — before asking anyone for a rupee. Every design choice in it cites a real system that came before and failed, for a specific, documented reason.",
  { x: 7.5, y: 4.5, w: 4.95, h: 1.9, fontSize: 12.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 17.5 });
aside(s, "Nothing here requires new behaviour — only a number worth saving.", M, 6.85, 9.5);
footer(s, 4);

// -------------------------------------------------------- 5 SOLUTION 1-3
s = p.addSlide(); bg(s);
kicker(s, "03 — How it works");
title(s, "One message, answered — start to finish");
lede(s, "Six steps. Most take under a minute. None of them ask the witness to do anything but send what they'd already send a friend.", M, 1.95, 7.6, 14);
const steps123 = [
  ["1", "Witness sends one WhatsApp", "Text, a voice note, or a photo — in English, Hinglish, or हिंदी, whatever's natural in the moment."],
  ["2", "Deterministic 112 gate", "Before any model reads the message, a fixed, code-level check looks for real emergencies and redirects them immediately — no AI in the loop for the moment that matters most."],
  ["3", "AI agent structures the report", "The message becomes a location (down to a DIGIPIN), a need, and an urgency level — a kit order is raised automatically: medical, food, or shelter."],
];
steps123.forEach(([n, h, b], i) => {
  const y0 = 2.95 + i * 1.4;
  s.addShape("ellipse", { x: M, y: y0, w: 0.42, h: 0.42, fill: { color: LAMP } });
  s.addText(n, { x: M, y: y0, w: 0.42, h: 0.42, fontSize: 15, bold: true, color: PAGE, fontFace: MONO, align: "center", valign: "middle", margin: 0 });
  s.addText(h, { x: M + 0.62, y: y0 - 0.05, w: 6.9, h: 0.34, fontSize: 14.5, bold: true, color: INK, fontFace: SANS, margin: 0 });
  s.addText(b, { x: M + 0.62, y: y0 + 0.3, w: 6.95, h: 0.95, fontSize: 12, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 16.5 });
});
s.addImage({ path: `${ASSETS}/phone.png`, x: 8.55, y: 1.95, w: 3.7, h: 3.68, rounding: true });
s.addText("the witness's phone — no app to install",
  { x: 8.55, y: 5.72, w: 3.75, h: 0.85, fontSize: 9, color: FAINT, fontFace: MONO, margin: 0, lineSpacing: 12.5 });
footer(s, 5);

// -------------------------------------------------------- 6 SOLUTION 4-6
s = p.addSlide(); bg(s);
kicker(s, "03 — How it works");
title(s, "…and it closes the loop");
const steps456 = [
  ["4", "Parallel offers, first accept wins", "The order goes out to the nearest trusted responders at once, like a ride-hailing request. Whoever accepts first gets the case; the rest stand down."],
  ["5", "Kit delivered, outcome recorded", "Served, escalated to clinical care, not found, or declined — every outcome is recorded, including a person's right to say no."],
  ["6", "The witness is told how it ended", "“Meena reached him, help was given. Thank you.” Not silence — an answer, which is the whole point."],
];
steps456.forEach(([n, h, b], i) => {
  const y0 = 2.15 + i * 1.4;
  s.addShape("ellipse", { x: M, y: y0, w: 0.42, h: 0.42, fill: { color: LAMP } });
  s.addText(n, { x: M, y: y0, w: 0.42, h: 0.42, fontSize: 15, bold: true, color: PAGE, fontFace: MONO, align: "center", valign: "middle", margin: 0 });
  s.addText(h, { x: M + 0.62, y: y0 - 0.05, w: 6.9, h: 0.34, fontSize: 14.5, bold: true, color: INK, fontFace: SANS, margin: 0 });
  s.addText(b, { x: M + 0.62, y: y0 + 0.3, w: 6.95, h: 0.95, fontSize: 12, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 16.5 });
});
s.addImage({ path: `${ASSETS}/resp-offer.png`, x: 8.55, y: 2.2, w: 4.15, h: 1.9, rounding: true });
s.addText("the responder's phone — accept, 3 minutes on the clock", { x: 8.55, y: 4.2, w: 4.2, h: 0.4, fontSize: 9, color: FAINT, fontFace: MONO, margin: 0 });
aside(s, "Value hypothesis: closing the loop turns one-time witnesses into repeat reporters — gratitude is the growth engine.", M, 6.55, 12.2);
footer(s, 6);

// -------------------------------------------------------------- 7 DEMO I
s = p.addSlide(); bg(s);
kicker(s, "04 — See it run");
title(s, "Not a mockup");
lede(s, "224 automated tests. Three real surfaces — control room, responder phone, witness phone — running the same loop end to end, offline, with zero paid API calls.", M, 1.95, 11.5, 14);
s.addImage({ path: `${ASSETS}/room.png`, x: M, y: 2.55, w: 7.15, h: 4.0, rounding: true });
s.addText("the control room, mid-shift — dispatch waves, kit stock, coordinator queue, live ops feed",
  { x: M, y: 6.62, w: 7.55, h: 0.3, fontSize: 9.5, color: FAINT, fontFace: MONO, margin: 0 });
[
  ["Control room", "Live map, dispatch waves, kit stock, kill-criteria dashboard."],
  ["Responder app", "Offer ping → checklist → outcome, on any phone."],
  ["Witness phone", "Trilingual chat, photo picker, live progress, a “still there?” check."],
].forEach(([h, b], i) => {
  const y0 = 2.7 + i * 1.42;
  s.addText(h, { x: 8.85, y: y0, w: 3.9, h: 0.32, fontSize: 13.5, bold: true, color: INK, fontFace: SANS, margin: 0 });
  s.addText(b, { x: 8.85, y: y0 + 0.34, w: 3.9, h: 0.9, fontSize: 11.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 16 });
});
footer(s, 7);

// ------------------------------------------------------------- 8 DEMO II
s = p.addSlide(); bg(s);
kicker(s, "04 — See it run");
title(s, "Dignity, and a paper trail");
lede(s, "What a responder sees at the pin, and what a coordinator sees behind every case.", M, 1.95, 10.5, 14);
s.addImage({ path: `${ASSETS}/resp-onsite.png`, x: M, y: 2.35, w: 2.15, h: 4.26, rounding: true });
s.addText("at the pin — greet, ask, don't assume, respect a no",
  { x: M, y: 6.65, w: 2.3, h: 0.45, fontSize: 9, color: FAINT, fontFace: MONO, margin: 0, lineSpacing: 12 });
s.addImage({ path: `${ASSETS}/coordinator.png`, x: 2.95, y: 2.35, w: 4.18, h: 4.26, rounding: true });
s.addText("the coordinator's view — full provenance, from report to order to outcome, HMAC-signed",
  { x: 2.95, y: 6.65, w: 4.3, h: 0.45, fontSize: 9, color: FAINT, fontFace: MONO, margin: 0, lineSpacing: 12 });
card(s, 7.55, 2.35, 5.23, 4.26, 0.12);
s.addText("ON RECORD", { x: 7.85, y: 2.65, w: 4.6, h: 0.3, fontSize: 10, color: LAMP, charSpacing: 2, fontFace: MONO, margin: 0 });
s.addText("Every case carries a signed trail — who reported it, what the agent inferred, which responder closed it. Witness reports and agent inferences are HMAC-tagged; a responder's observations are labelled as observations, never as fact.",
  { x: 7.85, y: 3.05, w: 4.6, h: 1.9, fontSize: 12, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 17 });
s.addText("Recorded 2:22 walkthrough and an interactive session replay available on request.",
  { x: 7.85, y: 5.1, w: 4.6, h: 1.4, fontSize: 12, italic: true, color: LAMP, fontFace: SERIF, margin: 0, lineSpacing: 17 });
footer(s, 8);

// ---------------------------------------------------------------- 9 CUSTOMER
s = p.addSlide(); bg(s);
kicker(s, "05 — Who pays");
title(s, "NGOs and CSR budgets, buying verified outcomes");
const cust = [
  ["Who buys", "NGO street-outreach programs and the CSR funders behind them — India mandates 2% of corporate profit to CSR — plus municipal shelter boards.", MED],
  ["Pain solved", "Outreach teams find people too late and blind; donors get activity reports, not verified outcomes; data practices now carry DPDP legal risk.", FOOD],
  ["What they get", "A per-zone service: verified need → delivered kit → coded outcome, with provenance-tagged records and privacy by architecture — audit-ready.", SHEL],
  ["First customer", "One Delhi NGO, one pilot zone — Nizamuddin. Reached through the Equitech network; NGO partner conversations start with this working demo. The pitch is a working demo, not a proposal.", GOOD],
];
cust.forEach(([h, b, c], i) => {
  const col = i % 2, row = Math.floor(i / 2);
  const x = M + col * 6.25, y0 = 2.0 + row * 2.35;
  card(s, x, y0, 5.95, 2.15, 0.1);
  dot(s, x + 0.3, y0 + 0.3, c, 0.16);
  s.addText(h, { x: x + 0.6, y: y0 + 0.18, w: 5.0, h: 0.38, fontSize: 14.5, bold: true, color: INK, fontFace: SANS, margin: 0 });
  s.addText(b, { x: x + 0.3, y: y0 + 0.65, w: 5.35, h: 1.4, fontSize: 12, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 16.5 });
});
aside(s, "Unit economics to defend in the pilot: ~₹300 kit + delivery ≈ ₹430 per person served — kill line at ₹900.", M, 6.85, 9.6);
footer(s, 9);

// -------------------------------------------------------------- 10 USERS
s = p.addSlide(); bg(s);
kicker(s, "06 — Who it's for");
title(s, "Three users, and one deliberate non-user");
const users = [
  ["THE WITNESS", "Any passer-by", "Uses only WhatsApp, nothing to install. Gets progress and closure, so they report again."],
  ["THE RESPONDER", "A vetted NGO field worker", "Gets the offer ping with kit, distance, and DIGIPIN. One tap records the outcome."],
  ["THE COORDINATOR", "NGO staff", "Watches the control room. Handles the edge cases the system refuses to guess at."],
];
users.forEach(([tag, h, b], i) => {
  const x = M + i * 4.18;
  card(s, x, 2.0, 3.92, 2.35, 0.1);
  s.addText(tag, { x: x + 0.32, y: 2.24, w: 3.3, h: 0.28, fontSize: 9.5, color: LAMP, charSpacing: 1.5, fontFace: MONO, margin: 0 });
  s.addText(h, { x: x + 0.32, y: 2.55, w: 3.3, h: 0.5, fontSize: 15, bold: true, color: INK, fontFace: SANS, margin: 0 });
  s.addText(b, { x: x + 0.32, y: 3.08, w: 3.35, h: 1.15, fontSize: 12, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 16.5 });
});
s.addShape("roundRect", { x: M, y: 4.6, w: 12.23, h: 1.85, rectRadius: 0.1, fill: { color: SURF }, line: { color: LINE, width: 1 } });
s.addText("The person in need is served — never enrolled.",
  { x: M + 0.35, y: 4.85, w: 11.5, h: 0.4, fontSize: 17, bold: true, color: INK, fontFace: SERIF, margin: 0 });
s.addText("No name, no photo of a face, no profile is ever stored. Exact locations are wiped once a case closes; after 90 days only coarse heat-cells remain. In a country that still criminalises begging, the strongest protection is that the dangerous database never exists.",
  { x: M + 0.35, y: 5.3, w: 11.5, h: 1.05, fontSize: 12.5, color: DIM, fontFace: SANS, margin: 0, lineSpacing: 18 });
aside(s, "Dignity is a design constraint, not a caption.", M, 6.85, 9.0);
footer(s, 10);

// ------------------------------------------------------------- 11 ROADMAP I
s = p.addSlide(); bg(s);
kicker(s, "07 — Roadmap");
title(s, "Three months to truth, twelve to scale — or an honest stop");
s.addText("NEXT 3 MONTHS — ONE ZONE, REAL PEOPLE", { x: M, y: 2.05, w: 6.0, h: 0.32, fontSize: 12, bold: true, color: MED, charSpacing: 1, fontFace: MONO, margin: 0 });
s.addText([
  { text: "Real WhatsApp number live — transport is built, onboarding is configuration", options: { bullet: { code: "2022" }, breakLine: true } },
  { text: "One NGO partner, 6–10 rostered responders, Nizamuddin pilot zone", options: { bullet: { code: "2022" }, breakLine: true } },
  { text: "Hindi/Hinglish voice-note speech-to-text bake-off (Sarvam vs Whisper)", options: { bullet: { code: "2022" }, breakLine: true } },
  { text: "8-week pilot measured against pre-registered kill criteria", options: { bullet: { code: "2022" } } },
], { x: M, y: 2.5, w: 6.1, h: 2.6, fontSize: 13.5, color: DIM, fontFace: SANS, margin: 0, paraSpaceAfter: 12, lineSpacing: 18 });
s.addText("BY 12 MONTHS — IF THE NUMBERS HOLD", { x: 7.15, y: 2.05, w: 6.0, h: 0.32, fontSize: 12, bold: true, color: SHEL, charSpacing: 1, fontFace: MONO, margin: 0 });
s.addText([
  { text: "Three zones, two partners — onboarding a partner is config plus a playbook", options: { bullet: { code: "2022" }, breakLine: true } },
  { text: "Voice-first reporting; DPDP audit and a published transparency report", options: { bullet: { code: "2022" }, breakLine: true } },
  { text: "Public dashboard of outcomes — the same one the funders see", options: { bullet: { code: "2022" } } },
], { x: 7.15, y: 2.5, w: 5.7, h: 2.3, fontSize: 13.5, color: DIM, fontFace: SANS, margin: 0, paraSpaceAfter: 12, lineSpacing: 18 });
card(s, M, 5.55, 12.23, 1.15, 0.1);
s.addText([
  { text: "Resources needed:  ", options: { bold: true, color: INK } },
  { text: "pilot grant (kits, responder stipends, WhatsApp + AI costs, DPIA/legal review) · partner introductions · mentorship on NGO ops.", options: { color: DIM } },
], { x: M + 0.3, y: 5.55, w: 11.6, h: 1.15, fontSize: 13, fontFace: SANS, margin: 0, lineSpacing: 18, valign: "middle" });
footer(s, 11);

// ------------------------------------------------------------ 12 ROADMAP II
s = p.addSlide(); bg(s);
kicker(s, "07 — Roadmap · kill criteria");
title(s, "Pre-registered, public before the pilot starts");
const killRows = [
  [{ text: "Kill criterion", options: { bold: true, color: FAINT, fontSize: 10.5, fontFace: MONO, fill: { color: SURF } } },
   { text: "Now", options: { bold: true, color: FAINT, fontSize: 10.5, fontFace: MONO, fill: { color: SURF } } },
   { text: "Target", options: { bold: true, color: FAINT, fontSize: 10.5, fontFace: MONO, fill: { color: SURF } } },
   { text: "Status", options: { bold: true, color: FAINT, fontSize: 10.5, fontFace: MONO, fill: { color: SURF } } }],
  [{ text: "Verified-need rate (found / closed)", options: { color: DIM, fontSize: 12.5 } },
   { text: "75%", options: { color: INK, fontSize: 12.5, fontFace: MONO } },
   { text: "≥ 40%", options: { color: DIM, fontSize: 12.5, fontFace: MONO } },
   { text: "✓ healthy", options: { color: GOOD, fontSize: 12.5, fontFace: MONO } }],
  [{ text: "Offer acceptance", options: { color: DIM, fontSize: 12.5 } },
   { text: "50%", options: { color: INK, fontSize: 12.5, fontFace: MONO } },
   { text: "≥ 50%", options: { color: DIM, fontSize: 12.5, fontFace: MONO } },
   { text: "✓ healthy", options: { color: GOOD, fontSize: 12.5, fontFace: MONO } }],
  [{ text: "Cost per person served", options: { color: DIM, fontSize: 12.5 } },
   { text: "₹580", options: { color: INK, fontSize: 12.5, fontFace: MONO } },
   { text: "≤ ₹900", options: { color: DIM, fontSize: 12.5, fontFace: MONO } },
   { text: "✓ healthy", options: { color: GOOD, fontSize: 12.5, fontFace: MONO } }],
  [{ text: "Open backlog", options: { color: DIM, fontSize: 12.5 } },
   { text: "11", options: { color: INK, fontSize: 12.5, fontFace: MONO } },
   { text: "≤ 12 capacity", options: { color: DIM, fontSize: 12.5, fontFace: MONO } },
   { text: "✓ healthy", options: { color: GOOD, fontSize: 12.5, fontFace: MONO } }],
];
s.addTable(killRows, {
  x: M, y: 2.05, w: 12.23, colW: [5.4, 2.3, 2.6, 1.93],
  border: { type: "solid", color: LINE, pts: 0.75 },
  fill: { color: PAGE }, autoPage: false, valign: "middle",
  rowH: 0.56,
});
s.addImage({ path: `${ASSETS}/metrics.png`, x: M, y: 5.0, w: 3.45, h: 1.66, rounding: true });
s.addText("the same dashboard the funders see — public before the pilot starts",
  { x: M, y: 6.72, w: 3.6, h: 0.28, fontSize: 8.5, color: FAINT, fontFace: MONO, margin: 0 });
s.addText("If Wayside stops earning its numbers, its own dashboard says so — and we publish that, and stop.",
  { x: 5.05, y: 5.05, w: 7.13, h: 1.6, fontSize: 16.5, italic: true, color: LAMP, fontFace: SERIF, margin: 0, lineSpacing: 22 });
footer(s, 12);

// ----------------------------------------------------------------- 13 CLOSE
s = p.addSlide(); bg(s);
s.addText([
  { text: "No cameras.\n", options: {} },
  { text: "No database of the poor.\n", options: {} },
  { text: "No one left by the wayside.", options: { color: LAMP } },
], { x: M, y: 1.7, w: 11.5, h: 2.7, fontSize: 40, bold: true, color: INK, fontFace: SERIF, margin: 0, lineSpacing: 52 });
s.addText("The ask: pilot funding for one zone · introductions to Delhi street-outreach NGOs · a mentor who has run field ops.",
  { x: M, y: 4.75, w: 11.6, h: 0.55, fontSize: 16, color: DIM, fontFace: SANS, margin: 0 });
s.addText("Rustom Dubash · rustommdubash@gmail.com · working demo, 2:22 video, and full research corpus on request",
  { x: M, y: 5.6, w: 12.0, h: 0.4, fontSize: 12.5, color: FAINT, fontFace: MONO, margin: 0 });
s.addShape("line", { x: M, y: 6.55, w: 4.5, h: 0, line: { color: LINE, width: 0.75 } });
s.addText("WAYSIDE — KEVIN XU INNOVATION CHALLENGE", { x: M, y: 6.7, w: 8, h: 0.3, fontSize: 9.5, color: LINE, charSpacing: 2, fontFace: MONO, margin: 0 });

p.writeFile({ fileName: path.join(__dirname, "wayside-kxic-pitch.pptx") })
  .then(() => console.log("written"));
