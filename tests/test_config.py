from app.config import Settings


def test_defaults():
    s = Settings(_env_file=None)
    assert s.app_name == "CallEye"
    assert s.gnani_mode == "mock"
    assert s.effective_mode == "mock"


def test_kill_switch_forces_mock():
    s = Settings(_env_file=None, gnani_mode="live", global_kill_switch=True)
    assert s.effective_mode == "mock"


def test_invite_set_parsing():
    s = Settings(_env_file=None, invite_codes="abc, DEF ,")
    assert s.invite_code_set == {"ABC", "DEF"}
