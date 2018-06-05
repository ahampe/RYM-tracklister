from __future__ import print_function
import codecs
import regex
import sys
from langdetect import detect

d = u'|'  # RYM's current tracklist delimiter

regs = [  # (regex) (0=byline/1=oneline, disc, track, title, min, sec)
    [r"^\b(\d+)[-.]?(\d*)\.?\s+(\S.*)\s+\b(\d+):(\d{1,2})\b", 0, 1, 2, 3, 4, 5],
    # If info is on separate lines, must combine all lines to search
    [r"^\b(\d+)[-.]?(?:\r\n)?(\d*)\.?(?:\r\n|\s+)\s?(\S.*)(?:\r\n)?\s*\b(\d+):(\d{1,2})\b", 1, 1, 2, 3, 4, 5],
    # Less strict searches: allow other duration formats, permit strict vinyl ("A1" but not "A")
    [r"^\b([A-Z]|\d+(?:[-.]))(\d+)\.?\s+(\S.*)\s+\b(\d+)[:'m](\d{1,2})[s\"]?\b", 0, 1, 2, 3, 4, 5],
    [r"^\b([A-Z]|\d+(?:[-.]))(\d+)\.?(?:\r\n|\s+)\s?(\S.*)(?:\r\n)?\s*\b(\d+)[:'m](\d{1,2})[s\"]?\b",
     1, 1, 2, 3, 4, 5],
    # Lenient vinyl: allow "A" and "A1"
    [r"^\b([A-Z])\W?(\d*)\.?\s+(\S.*)\s+\b(\d+)[:'m](\d{1,2})[s\"]?\b", 0, 1, 2, 3, 4, 5],
    [r"^\b([A-Z])(?:\r\n)?(\d*)\.?(?:\r\n|\s+)\s?(\S.*)(?:\r\n)?\s*\b(\d+)[:'m](\d{1,2})[s\"]?\b", 1, 1, 2, 3, 4, 5],
    # Allow trackno to start anywhere
    [r"\b(\d+)[-.]?(\d*)\.?\s+(\S.*)\s+\b(\d+)[:'m](\d{1,2})[s\"]?\b", 0, 1, 2, 3, 4, 5],
    [r"\b(\d+)[-.]?(?:\r\n)?(\d*)\.?(?:\r\n|\s+)\s?(\S.*)(?:\r\n)?\s*\b(\d+)[:'m](\d{1,2})[m\"]?\b", 1, 1, 2, 3, 4, 5],
    # All optional fields:
    [r"^\b(\d*)[-.]?(\d*)\.?\s+(\S.*)\s+\b(\d*):?(\d{0,2})\b$", 0, 1, 2, 3, 4, 5],
    # Less complete tracklistings:
    # No trackno. Just title and duration:
    [r"(.+)\s+\b(\d)[:'m](\d{1,2})[s\"]?\b", 0, 0, 0, 1, 2, 3],
    # No duration. Just trackno and title:
    [r"(\d+)\s+(.+)", 0, 1, 0, 2, 0, 0],
    # Maybe it's just the title
    [r"(.+)", 0, 0, 0, 1, 0, 0],
]

eng_lower_words = ['For', 'And', 'Of', 'In', 'But', 'On',
                   'A', 'An', 'The', 'Yet', 'So', 'Nor',
                   'Or', 'As', 'At', 'By', 'To', 'Vs.', 'Vs', 'V.',
                   'Etc', 'Etc.', "'N'", "O'"]
lowers = []
for lword in eng_lower_words:
    lowers.append(regex.compile(r'(?<![-!?:(".\u2014/\\])(?:\s)(' + regex.escape(
        lword) + r')(?:\s)(?![-!?:)\".\u2014/\\])'))

odd_reg = regex.compile(r'^(\w[A-Z]|\w\.\w)')
not_odd = regex.compile(r'^(\W*)(\w)')
new_cap = regex.compile(r'(!\s|\?\s|:\s|;\s|\"\s|\.\s|-\s|\u2014\s|/\s|\\\s|\(|\"|^)(\w)')
after_punc = regex.compile(r'(\w[-\'\u2019])(\w)')
long_dur = regex.compile(r'(\d+:\d+:\d+)')


def parse_tracklist_file(tracklist_path):
    tracklist_file = codecs.open(tracklist_path, encoding='utf-8-sig')
    return [x.strip() for x in tracklist_file.readlines() if len(x.strip()) > 0]


def parse_tracklist_str(tracklist_str):
    return [line.strip() for line in tracklist_str.split(u"\n") if len(line.strip()) > 0]


def track_list_write(tlines, capitalize=True):
    # First, fix long tracks (won't need to do this again)
    for i in range(len(tlines)):
        tlines[i] = long_dur.sub(fix_long_track, tlines[i])

    # There will be many search loops here, each more lenient than the last.
    # Using this method assumes all track data is written in the same format throughout.
    # Most strict is of the form "1-1. Title 1:00".
    # Later, period is optional, dash can be period,
    # any number of spaces/tabs can separate info fields,
    # and any non-alphanumeric can surround trackno or duration.
    rgxs = []
    funcs = []
    groups = []
    for line in regs:
        rgxs.append(regex.compile(line[0], flags=regex.M))
        funcs.append(reg_by_line if line[1] == '0' else reg_one_line)
        groups.append(line[2:])

    to_write = []
    oneline = u"\r\n".join(tlines)
    groups = [[int(z) for z in x] for x in groups]
    next_best = []
    for i in range(len(rgxs)):
        f = funcs[i]
        inp = oneline if f == reg_one_line else tlines
        to_write = f(rgxs[i], inp, *groups[i])
        if is_valid(to_write):
            break
        elif len(to_write) > len(next_best):
            next_best = to_write
    else:
        to_write = next_best

    if len(to_write) == 0:
        if len(next_best) > 0:
            to_write = next_best
        else:
            return  # Failure

    if capitalize:
        to_write = caps_format(to_write)

    # Formatting:
    formatted = []
    for line in to_write:
        disc, track, title, mins, secs = line
        if len(disc) == 0 or len(track) == 0:
            num = disc or track
        else:
            num = disc + '.' + track if disc.isdigit() else disc + track
        if len(mins) != 0 and len(secs) != 0:
            mins += ':'
        formatted.append(num + d + title + d + mins + secs)

    return formatted


def reg_by_line(compd, tlines, disc_g, tnum_g, title_g, min_g, sec_g):
    """
    For use with "Other" sources. Looks for track data using compiled regex "compd" and writes info for each track
    based on ints discG, tnumG, titleG, minG and secG. Assumes all info can be found on a single line.
    A zero (0) can be entered for any group_g that won't be matched.
    """
    to_write = []
    for i in range(len(tlines)):
        track_info = compd.search(tlines[i])
        if track_info:
            tr_num = track_info.group(tnum_g) if tnum_g else u""
            tr_disc = track_info.group(disc_g) if disc_g else u""
            tr_title = track_info.group(title_g)
            tr_min = strip_lead_zero(track_info.group(min_g)) if min_g else u""
            tr_sec = track_info.group(sec_g) if sec_g else u""
            to_write.append([tr_disc, tr_num, tr_title, tr_min, tr_sec])
    return to_write


def reg_one_line(compd, oneline, disc_g, tnum_g, title_g, min_g, sec_g):
    """
    Looks for track data using compiled regex "compd" and writes info for each track
    based on ints discG, tnumG, titleG, minG and secG. Looks at all lines at once.
    A zero (0) can be entered for any group_g that won't be matched.
    """
    to_write = []
    track_info = compd.search(oneline)
    while track_info:
        tr_num = track_info.group(tnum_g).strip() if tnum_g else u""
        tr_disc = track_info.group(disc_g).strip() if disc_g else u""
        tr_title = track_info.group(title_g).strip()
        tr_min = strip_lead_zero(track_info.group(min_g).strip()) if min_g else u""
        tr_sec = track_info.group(sec_g).strip() if sec_g else u""
        to_write.append([tr_disc, tr_num, tr_title, tr_min, tr_sec])

        # start next search from end of last match
        end_last = track_info.end(len(track_info.groups()))
        track_info = compd.search(oneline, end_last)
    return to_write


def is_valid(lines):
    """
    Verifies list output of regex searches
    :param lines: List of [disc#, track#, title, min, sec]
    :return: bool. True if lines is a valid tracklist
    """
    # Empty list is not valid:
    if len(lines) == 0:
        return False
    # Tracks and discs must be consistent (numbers vs alphanumeric vs empty)
    if len({(z[0].isdigit(), z[1].isdigit()) for z in lines}) > 1:
        return False
    # Track, disc cannot start with int > 1 or letter > a
    for k in (0, 1):
        if lines[0][k].isdigit() and int(lines[0][k]) > 1:
            return False
        elif lines[0][k] and lines[0][k][0].lower() > 'a':
            return False
    # Ordering must make sense:
    for i in range(1, len(lines)):
        if not is_step(lines[i][:2], lines[i-1][:2]):
            return False
    return True


def is_step(cur, prev):
    """
    Checks whether pairs cur (current) and prev (previous) are consecutive tracks.
    Works if disc_num or track_num is a single letter
    :param cur: [disc_num, track_num]
    :param prev: [disc_num, track_num]
    :return: bool. True if cur comes after prev, False otherwise
    """
    c = cur[:]
    c = [c[0] if len(c[0]) > 0 else '0', c[1] if len(c[1]) > 0 else '0']
    c = [ord(c[0])-64 if not c[0].isdigit() else int(c[0]),
         ord(c[1])-64 if not c[1].isdigit() else int(c[1])]
    p = prev[:]
    p = [p[0] if len(p[0]) > 0 else '0', p[1] if len(p[1]) > 0 else '0']
    p = [ord(p[0])-64 if not p[0].isdigit() else int(p[0]),
         ord(p[1])-64 if not p[1].isdigit() else int(p[1])]

    if c[0]-p[0] == 0:  # same disc, must be next track
        return c[1]-p[1] == 1
    elif c[0]-p[0] == 1:  # next disc, must start new track
        return c[1] < 2
    else:  # cannot be valid
        return False


def strip_lead_zero(s):
    """
    For track durations, trims any 0 at the beginning as long as there's at least 1 character (in front of colon).
    """
    if len(s) == 0:
        return s
    while s[0] == '0' and len(s) > 1:
        if s[1] == ':':
            break
        s = s[1:]
    return s


def fix_long_track(m):
    """
    For turning ##:##:## durations into standard RYM ###:## durations
    m is a regex match object.
    """
    r = m.group(0).split(':')
    fixed_min = int(r[0]) * 60 + int(r[1])
    return str(fixed_min) + ":" + str(r[2])


# ----Capitalization functions----

def spaced_lower_word(match):
    # Replace matched uppercase words
    return u' ' + match.group(1).lower() + u' '


def upper_group2(match):
    # Capitalize the first letter of each word
    return match.group(1) + match.group(2).upper()


def lower_group2(match):
    # Un-capitalize the first letter of each word
    return match.group(1) + match.group(2).lower()


def caps_format(tw):
    """
    Takes tracklist and capitalizes titles "correctly". Does not recognize proper nouns.
    Currently only works properly for English. Other languages are titled with first letter capitalized only
    """
    titles = [t[2] for t in tw]
    joined_titles = " ".join(titles)
    try:
        lang = detect(joined_titles)
    except:
        lang = "en"

    if lang == 'en':
        for i, s in enumerate(titles):
            s_list = s.split()
            for n in range(len(s_list)):
                odd_case = odd_reg.search(s_list[n])
                if not odd_case:
                    s_list[n] = not_odd.sub(upper_group2, s_list[n])
            s = u" ".join(s_list)
            # Only substitute words bound by spaces on both sides
            # ...and with no major punctuation surrounding:
            for reglo in lowers:
                s = reglo.sub(spaced_lower_word, s)
            titles[i] = s
    else:  # Turn every word except the first to lowercase.
        for i, s in enumerate(titles):
            s_list = s.split()
            for n in range(len(s_list)):
                odd_case = odd_reg.search(s_list[n])
                if not odd_case:
                    s_list[n] = not_odd.sub(lower_group2, s_list[n])
                    # Also, lowercase letters after apostrophes and hyphens:
                    s_list[n] = after_punc.sub(lower_group2, s_list[n])
            s = u" ".join(s_list)
            # Now capitalize new statements:
            s = new_cap.sub(upper_group2, s)
            titles[i] = s
    for j, title in enumerate(titles):
        tw[j][2] = title
    return tw
