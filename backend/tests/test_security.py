import pytest

from app.utils.security import check_password_strength, get_password_hash, verify_password


class TestPasswordHash:
    def test_hash_and_verify_roundtrip(self):
        password = "MySecret123"
        hashed = get_password_hash(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        password = "MySecret123"
        hashed = get_password_hash(password)
        assert verify_password("WrongPassword", hashed) is False


class TestPasswordStrength:
    def test_too_short(self):
        assert check_password_strength("Ab1") is False
        assert check_password_strength("Abcdef1") is False

    def test_exactly_8_chars_with_two_categories(self):
        assert check_password_strength("Abcdef12") is True

    def test_only_lowercase(self):
        assert check_password_strength("abcdefgh") is False

    def test_only_uppercase(self):
        assert check_password_strength("ABCDEFGH") is False

    def test_only_digits(self):
        assert check_password_strength("12345678") is False

    def test_upper_and_lower(self):
        assert check_password_strength("Abcdefgh") is True

    def test_lower_and_digit(self):
        assert check_password_strength("abcdefg1") is True

    def test_upper_and_special(self):
        assert check_password_strength("ABCDEFG!") is True

    def test_three_categories(self):
        assert check_password_strength("Abcdef1!") is True

    def test_four_categories(self):
        assert check_password_strength("Abcdef1!") is True

    def test_empty_string(self):
        assert check_password_strength("") is False

    def test_long_password_single_category(self):
        assert check_password_strength("a" * 100) is False
