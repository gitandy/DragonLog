"""Module contains the regular expression for field validation"""
import re

REGEX_CALL = re.compile(r'([a-zA-Z0-9]{1,3}?/)?[a-zA-Z0-9]{1,3}?[0-9][a-zA-Z0-9]{0,3}?[a-zA-Z](/[aAmMpPrRtT]{1,2}?)?')
REGEX_RSTFIELD = re.compile(r'[1-5][1-9][1-9aAcCkKmMsSxX]?')
REGEX_LOCATOR = re.compile(r'[a-rA-R]{2}[0-9]{2}([a-xA-X]{2}([0-9]{2})?)?')


def check_format(exp: re.Pattern, txt: str) -> bool:
    """Test the given text against a regular expression
    :param exp: a compiled pattern
    :param txt: a text
    :return: true if pattern matches"""
    return bool(re.fullmatch(exp, txt))
