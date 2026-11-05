from app.detector.engine import SessionAnalyzer


def run_call(segments):
    az = SessionAnalyzer()
    for seg in segments:
        az.analyze_update(seg["text"], True, float(seg["t"]))
    return az


def test_scam_digital_arrest_red():
    az = run_call([
        {"t": 0, "text": "main police thana se bol raha hoon"},
        {"t": 3, "text": "aapke naam par case darj hua hai"},
        {"t": 6, "text": "aapko arrest ho sakta hai"},
        {"t": 9, "text": "kisi ko nahi batana"},
        {"t": 12, "text": "bail ke liye paise transfer karo"},
        {"t": 13, "text": "mujhe aapka OTP chahiye"},
    ])
    assert az.decision.label == "red"


def test_genuine_otp_warning_green():
    az = run_call([
        {"t": 0, "text": "bank account me transaction hui hai"},
        {"t": 3, "text": "kisi ko OTP mat batana"},
        {"t": 6, "text": "bank kabhi bhi OTP nahi maangta"},
    ])
    assert az.decision.label == "green"


def test_emergency_without_money_is_amber():
    az = run_call([
        {"t": 0, "text": "aapke bete ko accident ho gaya hai"},
        {"t": 3, "text": "wo hospital me bharti hai, jaldi aaiye"},
    ])
    assert az.decision.label == "amber"


def test_emergency_with_money_demand_red():
    az = run_call([
        {"t": 0, "text": "aapke bete ko accident ho gaya hai"},
        {"t": 3, "text": "main police hoon, kisi ko mat batana"},
        {"t": 6, "text": "bail ke liye turant paise transfer karo"},
        {"t": 9, "text": "mujhe aapka OTP do"},
    ])
    assert az.decision.label == "red"


def test_dev_latches():
    az = run_call([
        {"t": 0, "text": "mujhe aapka OTP chahiye"},
        {"t": 20, "text": "aapka parcel deliver ho gaya hai"},  # innocent later
    ])
    assert az.decision.label == "red"


def test_kyc_otp_ask_is_red():
    # "nahi" in an earlier sentence must not mask the OTP ask.
    az = run_call([
        {"t": 0, "text": "aapke KYC update karne ka time aa gaya hai"},
        {"t": 3, "text": "aapka account block ho jayega agar update nahi kiya"},
        {"t": 6, "text": "mujhe aapka OTP aur card details chahiye"},
    ])
    assert az.decision.label == "red"


def test_lottery_prize_fee_is_amber():
    az = run_call([
        {"t": 0, "text": "aapne lottery jeeta hai"},
        {"t": 3, "text": "prize ke liye ek fee pay karni hogi"},
        {"t": 6, "text": "aaj hi payment karo, warna prize khatam ho jayega"},
    ])
    assert az.decision.label == "amber"


def test_pressure_rises_with_urgency():
    az = run_call([
        {"t": 0, "text": "hello"},
        {"t": 3, "text": "turant karo, der mat karo"},
    ])
    assert az.meter.pressure > 0
