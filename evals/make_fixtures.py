#!/usr/bin/env python3
"""Build synthetic screenshots with ground truth for the borges-ipsum evals.

Each fixture is a PNG plus a JSON file recording every word box and whether a
correct run must replace it ("redact") or leave it ("keep"), and every non-text
element (icons, rules, buttons) that must survive. The text is invented PII of
the kind people forget to scrub: names, emails, hostnames, tokens, paths.
"""
import json
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fixtures")

FONTS = {
    "mono": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "mono-bold": "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "sans": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "sans-bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "serif": "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
}

PII = """Priya Raman priya.raman@northwind-labs.io deploy-bot ghp_8fK2xQ7mLw prod-db-03
10.14.2.71 /home/jsmith/work/acme-billing invoice #48213 Jordan Okafor staging
api.northwind-labs.io sk_live_51Hx Q3 roadmap Marisol Vega customer Globex payroll
migration rollback merged PR 1287 into main the auth token expires Thursday
ticket OPS-7731 Hollis Grant on-call pager escalated to Dana Whitfield salary
review offer letter SSN ending 4417 meeting with legal about the Initech contract
repo northwind/ledger-core branch fix/refund-race build 9921 failed on runner-7
password reset for kpatel the vendor quote was 48,000 dollars approved by finance""".split()


class Canvas:
    def __init__(self, name, w, h, bg):
        self.name = name
        self.img = Image.new("RGB", (w, h), bg)
        self.d = ImageDraw.Draw(self.img)
        self.words, self.objects = [], []
        self.rng = random.Random(name)

    def text(self, x, y, s, font, size, color, expect="redact"):
        f = ImageFont.truetype(FONTS[font], size)
        space = f.getlength(" ")
        for word in s.split():
            self.d.text((x, y), word, font=f, fill=color)
            l, t, r, b = self.d.textbbox((x, y), word, font=f)
            self.words.append({"box": [int(l), int(t), int(r + 0.999), int(b + 0.999)], "text": word, "expect": expect})
            x += f.getlength(word) + space
        return x

    def para(self, x, y, width, n_lines, font, size, color, expect="redact", leading=1.55):
        f = ImageFont.truetype(FONTS[font], size)
        for _ in range(n_lines):
            line, cx = [], 0
            while True:
                w = self.rng.choice(PII)
                if cx + f.getlength(w) > width:
                    break
                line.append(w)
                cx += f.getlength(w + " ")
            self.text(x, y, " ".join(line), font, size, color, expect)
            y += int(size * leading)
        return y

    def obj(self, kind, box, **style):
        shape = {"rect": self.d.rectangle, "ellipse": self.d.ellipse,
                 "rounded": self.d.rounded_rectangle}[kind]
        shape(box, **style)
        self.objects.append({"box": list(box), "kind": kind})

    def save(self, task):
        os.makedirs(OUT, exist_ok=True)
        self.img.save(os.path.join(OUT, self.name + ".png"))
        with open(os.path.join(OUT, self.name + ".json"), "w") as fh:
            json.dump({"image": self.name + ".png", "task": task,
                       "size": self.img.size, "words": self.words,
                       "objects": self.objects}, fh, indent=1)


def dark_chat():
    c = Canvas("dark-chat", 1600, 900, (22, 22, 24))
    c.d.rectangle([0, 0, 1600, 40], fill=(40, 40, 44))
    c.text(20, 10, "Finder File Edit View Window", "sans-bold", 18, (235, 235, 235), "keep")
    c.d.rectangle([0, 40, 300, 900], fill=(30, 30, 33))
    y = 70
    for _ in range(12):
        c.obj("ellipse", (20, y + 2, 40, y + 22), fill=(230, 120, 60))
        label = " ".join(c.rng.sample(PII, 2))[:21]  # sidebars truncate
        c.text(55, y, label, "mono", 17, (210, 210, 210))
        y += 44
    c.obj("rect", (300, 40, 302, 900), fill=(70, 70, 75))
    y = c.para(340, 80, 1180, 6, "mono", 18, (225, 225, 225))
    c.d.rounded_rectangle([700, y + 20, 1540, y + 150], radius=14, fill=(48, 48, 52))
    c.para(730, y + 42, 780, 3, "mono", 18, (240, 240, 240))
    y += 190
    c.obj("rect", (340, y, 1540, y + 2), fill=(90, 120, 220))
    y = c.para(340, y + 30, 1180, 4, "mono-bold", 18, (250, 250, 250))
    c.para(340, y + 10, 1180, 2, "mono", 14, (130, 130, 135))
    c.obj("rounded", (1480, 830, 1530, 880), radius=10, fill=(90, 90, 95))
    c.save("Replace all private text with Borges ipsum. Keep the menu bar at the top "
           "(the first 40 pixels) as it is.")


def light_doc():
    c = Canvas("light-doc", 1400, 1000, (252, 252, 250))
    c.text(80, 50, "Quarterly incident review", "serif", 44, (20, 20, 20))
    y = c.para(80, 140, 1240, 5, "sans", 22, (40, 40, 40))
    c.obj("rect", (80, y + 10, 1320, y + 12), fill=(200, 200, 200))
    y = c.para(80, y + 40, 1240, 3, "sans", 22, (30, 90, 200))
    c.d.rounded_rectangle([80, y + 10, 900, y + 70], radius=8, fill=(232, 232, 236))
    c.text(100, y + 25, "ssh deploy@prod-db-03 --key ~/.ssh/acme", "mono", 22, (50, 50, 60))
    y += 110
    for i in range(4):
        c.obj("rect", (82, y + 6 + i * 40, 98, y + 22 + i * 40), outline=(80, 80, 80), width=2)
        c.text(115, y + i * 40, " ".join(c.rng.sample(PII, 4)), "sans", 20, (40, 40, 40))
    c.para(80, y + 190, 1240, 2, "sans", 15, (120, 120, 120))
    c.save("Anonymize every piece of text in this screenshot with Borges ipsum.")


def mixed_panes():
    c = Canvas("mixed-panes", 1500, 800, (255, 255, 255))
    c.d.rectangle([0, 0, 420, 800], fill=(28, 30, 36))
    y = 40
    for _ in range(14):
        c.obj("rect", (24, y + 4, 40, y + 20), fill=(110, 200, 140))
        c.text(56, y, " ".join(c.rng.sample(PII, 2))[:28], "sans", 19, (220, 222, 228))
        y += 50
    c.text(470, 40, "Settings", "sans-bold", 30, (20, 20, 20), "keep")
    y = c.para(470, 110, 960, 4, "sans", 21, (50, 50, 50))
    c.d.rounded_rectangle([470, y + 20, 1430, y + 140], radius=12, fill=(30, 30, 30))
    c.para(500, y + 45, 900, 2, "mono", 20, (120, 230, 140))
    c.obj("rounded", (1300, 700, 1440, 750), radius=10, fill=(40, 110, 230))
    c.save("Replace the text with Borges ipsum, except the 'Settings' heading near the "
           "top of the white pane, which is generic and should stay.")


def colorful():
    c = Canvas("colorful", 1300, 700, (240, 236, 228))
    c.d.rectangle([0, 0, 1300, 90], fill=(64, 38, 120))
    c.text(40, 22, "Northwind Labs status", "sans-bold", 36, (255, 255, 255))
    y = c.para(40, 130, 1220, 4, "serif", 24, (90, 30, 30))
    c.d.rectangle([40, y + 20, 1260, y + 200], fill=(255, 214, 102))
    c.para(70, y + 45, 1160, 4, "sans", 21, (60, 40, 0))
    c.obj("ellipse", (1180, 600, 1240, 660), fill=(64, 38, 120))
    c.save("Swap every bit of text for Borges ipsum.")


def retina():
    # A 2x capture: every size doubles, and the heading outgrows --max-height 60.
    c = Canvas("retina", 2880, 1600, (24, 26, 30))
    c.d.rectangle([0, 0, 2880, 56], fill=(44, 46, 52))
    c.text(36, 12, "Mail Edit View Mailbox Message", "sans-bold", 28, (230, 230, 230), "keep")
    c.text(120, 140, "Re: Initech contract", "sans-bold", 76, (245, 245, 245))
    c.obj("ellipse", (120, 290, 200, 370), fill=(200, 90, 120))
    c.text(230, 305, "Marisol Vega to Dana Whitfield", "sans", 34, (200, 200, 205))
    y = c.para(120, 430, 2600, 8, "sans", 34, (225, 225, 225))
    c.para(120, y + 40, 2600, 2, "mono", 30, (140, 200, 255))
    c.save("Replace all private text with Borges ipsum. Keep the macOS menu bar at the top.")


def faint_bold():
    # Placeholder-grey text below the default contrast and a heavy display heading.
    c = Canvas("faint-bold", 1400, 900, (252, 252, 250))
    c.text(70, 40, "Hollis Grant payroll", "sans-bold", 62, (15, 15, 15))
    y = c.para(70, 150, 1260, 4, "sans", 21, (45, 45, 45))
    c.obj("rounded", (70, y + 20, 900, y + 76), radius=8, outline=(205, 205, 205), width=2)
    c.text(90, y + 34, "priya.raman@northwind-labs.io", "sans", 20, (226, 226, 226))
    c.text(70, y + 110, "Last edited by Jordan Okafor", "sans", 16, (222, 222, 220))
    c.para(70, y + 160, 1260, 3, "serif", 22, (40, 40, 40))
    c.save("Anonymize every piece of text in this screenshot with Borges ipsum, "
           "including faint placeholder text.")


def media():
    # Text over a gradient and a photo, next to an avatar and a QR code that must survive.
    rng = random.Random("media")
    c = Canvas("media", 1400, 900, (245, 245, 245))
    for x in range(1400):  # gradient banner
        t = x / 1400
        c.d.line([(x, 0), (x, 120)], fill=(int(40 + 160 * t), 60, int(160 - 100 * t)))
    c.text(40, 36, "Globex quarterly offsite", "sans-bold", 40, (255, 255, 255))
    # "photo": soft blobs with a caption on top
    from PIL import ImageFilter
    photo = Image.new("RGB", (560, 380))
    pd = ImageDraw.Draw(photo)
    for _ in range(40):
        x, y, r = rng.randrange(560), rng.randrange(380), rng.randrange(30, 120)
        pd.ellipse([x - r, y - r, x + r, y + r], fill=tuple(rng.randrange(60, 200) for _ in range(3)))
    c.img.paste(photo.filter(ImageFilter.GaussianBlur(18)), (40, 160))
    c.objects.append({"box": [40, 160, 600, 480], "kind": "photo", "text_inside": True})
    c.text(60, 430, "Dana Whitfield, Lisbon", "sans-bold", 26, (255, 255, 255))
    # avatar
    face = Image.new("RGB", (120, 120), (210, 170, 140))
    fd = ImageDraw.Draw(face)
    fd.ellipse([30, 30, 50, 50], fill=(40, 30, 30))
    fd.ellipse([70, 30, 90, 50], fill=(40, 30, 30))
    fd.arc([30, 50, 90, 95], 20, 160, fill=(120, 40, 40), width=5)
    c.img.paste(face, (660, 170))
    c.objects.append({"box": [660, 170, 780, 290], "kind": "avatar"})
    c.text(800, 200, "Hollis Grant", "sans-bold", 26, (30, 30, 30))
    c.text(800, 240, "hollis@globex.example", "sans", 20, (90, 90, 90))
    # QR-like code: 6 px modules, finer than the stroke filter
    q0x, q0y, mod = 1100, 170, 6
    c.d.rectangle([q0x - 12, q0y - 12, q0x + 25 * mod + 12, q0y + 25 * mod + 12], fill=(255, 255, 255))
    for i in range(25):
        for j in range(25):
            corner = (i < 7 and j < 7) or (i < 7 and j > 17) or (i > 17 and j < 7)
            on = (corner and (i % 6 == 0 or j % 6 == 0 or (i % 6 in (2, 3, 4) and j % 6 in (2, 3, 4)))) \
                if corner else rng.random() < 0.5
            if on:
                c.d.rectangle([q0x + j * mod, q0y + i * mod, q0x + j * mod + mod - 1, q0y + i * mod + mod - 1],
                              fill=(0, 0, 0))
    c.objects.append({"box": [q0x, q0y, q0x + 25 * mod, q0y + 25 * mod], "kind": "qr"})
    c.para(660, 520, 700, 6, "sans", 21, (40, 40, 40))
    c.save("Swap every bit of text for Borges ipsum before I post this. "
           "Tell me about anything you could not anonymize.")


def chrome():
    # The keep is a judgement: generic labels stay, anything identifying goes.
    c = Canvas("chrome", 1500, 860, (250, 250, 252))
    c.d.rectangle([0, 0, 1500, 44], fill=(232, 232, 236))
    c.text(18, 12, "File Edit View Go Help", "sans", 18, (30, 30, 30), "keep")
    c.d.rectangle([0, 44, 260, 860], fill=(240, 240, 244))
    y = 70
    for label in ("Inbox", "Drafts", "Sent", "Archive", "Spam", "Trash"):
        c.text(28, y, label, "sans", 19, (40, 40, 40), "keep")
        y += 38
    c.text(28, y + 20, "Labels", "sans-bold", 15, (110, 110, 110), "keep")
    y += 56
    for _ in range(4):
        c.text(28, y, " ".join(c.rng.sample(PII, 2))[:20], "sans", 18, (40, 40, 40))
        y += 36
    y = 70
    for _ in range(9):
        c.text(290, y, " ".join(c.rng.sample(PII, 2))[:22], "sans-bold", 18, (20, 20, 20))
        c.text(560, y, " ".join(c.rng.sample(PII, 9))[:80], "sans", 18, (90, 90, 90))
        c.obj("rect", (290, y + 34, 1470, y + 35), fill=(225, 225, 230))
        y += 52
    c.save("Keep generic app chrome such as the menu bar and folder names like Inbox "
           "and Sent. Replace anything that could identify a person, company or project.")


BUILDS = [dark_chat, light_doc, mixed_panes, colorful, retina, faint_bold, media, chrome]

if __name__ == "__main__":
    for build in BUILDS:
        build()
    print("fixtures written to", OUT)
