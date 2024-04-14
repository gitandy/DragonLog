"""Module contains the regular expression for field validation"""
import re

REGEX_CALL = re.compile(r'([a-zA-Z0-9]{1,3}?/)?([a-zA-Z0-9]{1,3}?[0-9][a-zA-Z0-9]{0,3}?[a-zA-Z])(/[aAmMpPrRtT]{1,2}?)?')
REGEX_RSTFIELD = re.compile(r'([1-5][1-9][1-9aAcCkKmMsSxX]?)|([rR]?[-+]?[0-9]{1,2})')
REGEX_LOCATOR = re.compile(r'[a-rA-R]{2}[0-9]{2}([a-xA-X]{2}([0-9]{2})?)?')
REGEX_NONASCII = re.compile(r'[ -~\n\r]*(.)?')
REGEX_TIME = re.compile(r'(([0-1][0-9])|(2[0-3])):([0-5][0-9])(:[0-5][0-9])?')

def check_format(exp: re.Pattern, txt: str) -> bool:
    """Test the given text against a regular expression
    :param exp: a compiled pattern
    :param txt: a text
    :return: true if pattern matches"""
    return bool(re.fullmatch(exp, txt))

def check_call(call: str) -> None|tuple:
    """Test a call sign against a regular expression
    :param call: a call sign
    :return: tuple of parts ('Country prefix/', 'Call sign', '/Operation suffix')"""

    m = re.fullmatch(REGEX_CALL, call)
    if m:
        return m.groups()

def find_non_ascii(text: str) -> set:
    return set(re.findall(REGEX_NONASCII, text))
