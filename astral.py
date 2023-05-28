# Cutdown version astal.py that will work with circut python and
# suports the just the calculations we're intrested in.
#
# Adapted from the https://github.com/sffjunkie/astral project.

from math import cos, sin, tan, acos, asin
from math import radians, degrees

# Just enough of the functionality of the datetime.Date class to
# support Astral. Much of this is lifted directly from datetime.py.

def _cmp(x, y):
    return 0 if x == y else 1 if x > y else -1

# Utility functions, adapted from Python's Demo/classes/Dates.py, which
# also assumes the current Gregorian calendar indefinitely extended in
# both directions.  Difference:  Dates.py calls January 1 of year 0 day
# number 1.  The code here calls January 1 of year 1 day number 1.  This is
# to match the definition of the "proleptic Gregorian" calendar in Dershowitz
# and Reingold's "Calendrical Calculations", where it's the base calendar
# for all computations.  See the book for algorithms for converting between
# proleptic Gregorian ordinals and many other calendar systems.

# -1 is a placeholder for indexing purposes.
_DAYS_IN_MONTH = [-1, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

_DAYS_BEFORE_MONTH = [-1]  # -1 is a placeholder for indexing purposes.
dbm = 0
for dim in _DAYS_IN_MONTH[1:]:
    _DAYS_BEFORE_MONTH.append(dbm)
    dbm += dim
del dbm, dim

def _is_leap(year):
    "year -> 1 if leap year, else 0."
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

def _days_before_year(year):
    "year -> number of days before January 1st of year."
    y = year - 1
    return y*365 + y//4 - y//100 + y//400

def _days_in_month(year, month):
    "year, month -> number of days in that month in that year."
    assert 1 <= month <= 12, month
    if month == 2 and _is_leap(year):
        return 29
    return _DAYS_IN_MONTH[month]

def _days_before_month(year, month):
    "year, month -> number of days in year preceding first day of month."
    assert 1 <= month <= 12, 'month must be in 1..12'
    return _DAYS_BEFORE_MONTH[month] + (month > 2 and _is_leap(year))

def _ymd2ord(year, month, day):
    "year, month, day -> ordinal, considering 01-Jan-0001 as day 1."
    assert 1 <= month <= 12, 'month must be in 1..12'
    dim = _days_in_month(year, month)
    assert 1 <= day <= dim, ('day must be in 1..%d' % dim)
    return (_days_before_year(year) +
            _days_before_month(year, month) +
            day)

_DI400Y = _days_before_year(401)    # number of days in 400 years
_DI100Y = _days_before_year(101)    #    "    "   "   " 100   "
_DI4Y   = _days_before_year(5)      #    "    "   "   "   4   "

def _ord2ymd(n):
    "ordinal -> (year, month, day), considering 01-Jan-0001 as day 1."

    # n is a 1-based index, starting at 1-Jan-1.  The pattern of leap years
    # repeats exactly every 400 years.  The basic strategy is to find the
    # closest 400-year boundary at or before n, then work with the offset
    # from that boundary to n.  Life is much clearer if we subtract 1 from
    # n first -- then the values of n at 400-year boundaries are exactly
    # those divisible by _DI400Y:
    #
    #     D  M   Y            n              n-1
    #     -- --- ----        ----------     ----------------
    #     31 Dec -400        -_DI400Y       -_DI400Y -1
    #      1 Jan -399         -_DI400Y +1   -_DI400Y      400-year boundary
    #     ...
    #     30 Dec  000        -1             -2
    #     31 Dec  000         0             -1
    #      1 Jan  001         1              0            400-year boundary
    #      2 Jan  001         2              1
    #      3 Jan  001         3              2
    #     ...
    #     31 Dec  400         _DI400Y        _DI400Y -1
    #      1 Jan  401         _DI400Y +1     _DI400Y      400-year boundary
    n -= 1
    n400, n = divmod(n, _DI400Y)
    year = n400 * 400 + 1   # ..., -399, 1, 401, ...

    # Now n is the (non-negative) offset, in days, from January 1 of year, to
    # the desired date.  Now compute how many 100-year cycles precede n.
    # Note that it's possible for n100 to equal 4!  In that case 4 full
    # 100-year cycles precede the desired day, which implies the desired
    # day is December 31 at the end of a 400-year cycle.
    n100, n = divmod(n, _DI100Y)

    # Now compute how many 4-year cycles precede it.
    n4, n = divmod(n, _DI4Y)

    # And now how many single years.  Again n1 can be 4, and again meaning
    # that the desired day is December 31 at the end of the 4-year cycle.
    n1, n = divmod(n, 365)

    year += n100 * 100 + n4 * 4 + n1
    if n1 == 4 or n100 == 4:
        assert n == 0
        return year-1, 12, 31

    # Now the year is correct, and n is the offset from January 1.  We find
    # the month via an estimate that's either exact or one too large.
    leapyear = n1 == 3 and (n4 != 24 or n100 == 3)
    assert leapyear == _is_leap(year)
    month = (n + 50) >> 5
    preceding = _DAYS_BEFORE_MONTH[month] + (month > 2 and leapyear)
    if preceding > n:  # estimate is too large
        month -= 1
        preceding -= _DAYS_IN_MONTH[month] + (month == 2 and leapyear)
    n -= preceding
    assert 0 <= n < _days_in_month(year, month)

    # Now the year and month are correct, and n is the offset from the
    # start of that month:  we're done!
    return year, month, n+1

class Date:
    def __init__(self, year, month, day):
        self._year = year
        self._month = month
        self._day = day

    @classmethod
    def fromtimestamp(cls, timestamp):
        return cls(timestamp.tm_year, timestamp.tm_mon, timestamp.tm_mday)
        
    @classmethod
    def fromordinal(cls, n):
        """Construct a date from a proleptic Gregorian ordinal.
        January 1 of year 1 is day 1.  Only the year, month and day are
        non-zero in the result.
        """
        y, m, d = _ord2ymd(n)
        return cls(y, m, d)

    @property
    def year(self):
        """year (1-9999)"""
        return self._year

    @property
    def month(self):
        """month (1-12)"""
        return self._month

    @property
    def day(self):
        """day (1-31)"""
        return self._day
    
    def toordinal(self):
        """Return proleptic Gregorian ordinal for the year, month and day.
        January 1 of year 1 is day 1.  Only the year, month and day values
        contribute to the result.
        """
        return _ymd2ord(self._year, self._month, self._day)

    def tomarrow(self):
        ordinal = self.toordinal() + 1
        return self.fromordinal(ordinal)

    def yesterday(self):
        ordinal = self.toordinal() - 1
        return self.fromordinal(ordinal)

    def __sub__(self, b):
        return self.toordinal() - b.toordinal()

    def __str__(self):
        return "%4d-%02d-%02d" % (self._year, self._month, self._day)

    def __gt__(self, other):
        return self.toordinal() > other.toordinal()

    def __lt__(self, other):
        return self.toordinal() < other.toordinal()

    def __eq__(self, other):
        return self.toordinal() == other.toordinal()

def excel_datediff(start_date, end_date):
    """Return the same number of days between 2 dates as Excel does"""
    return end_date.toordinal() - start_date.toordinal() + 2

SECS_PER_DAY = 24 * 60 * 60

class DateSeconds:
    """Like DateTime, but just seconds since midnight for the time instead of hours, minutes, seconds."""

    def __init__(self, date, seconds):
        while seconds >= SECS_PER_DAY:
            seconds -= SECS_PER_DAY
            date = date.tomarrow()

        while seconds < 0:
            seconds += SECS_PER_DAY
            date = date.yesterday()

        self._seconds = seconds
        self._date = date

    @classmethod
    def fromtimestamp(cls, ts):
        date = Date.fromtimestamp(ts)
        seconds = ts.tm_hour * 3600 + ts.tm_min * 60 + ts.tm_sec
        return cls(date, seconds)

    @property
    def date(self):
        return self._date

    @property
    def seconds(self):
        return self._seconds

    def toordinal(self):
        return self._date.toordinal() * SECS_PER_DAY + self._seconds

    def __sub__(self, b):
        return self.toordinal() - b.toordinal()
    
    def __str__(self):
        return f"{self.date} {self.seconds}"

    def __gt__(self, other):
        return self.toordinal() > other.toordinal()

    def __lt__(self, other):
        return self.toordinal() < other.toordinal()

    def __ge__(self, other):
        return self.toordinal() >= other.toordinal()

    def __le__(self, other):
        return self.toordinal() <= other.toordinal()

    def __eq__(self, other):
        return self.toordinal() == other.toordinal()


SUN_RISING = 1
SUN_SETTING = -1
_NAMED_DEPRESSIONS = {"civil": 6, "nautical": 12, "astronomical": 18}

def _depression(depression):
    if isinstance(depression, str) or isinstance(depression, ustr):
        try:
            return _NAMED_DEPRESSIONS[depression]
        except KeyError:
            raise KeyError(
                "solar_depression must be either a number "
                "or one of: %s" % tuple(_NAMED_DEPRESSIONS.keys)
            )
    else:
        return float(depression)

def solar_noon_utc(date, latitude, longitude):
    try:
        return _calc_time(0, 0, date, latitude, longitude)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise AstralError(
                ("Sun never reaches directly above on this day, " "at this location.")
            )
        else:
            raise

def time_of_first_after(event, t, latitude, longitude):
    """Return the time of the first event (a function like sunrise_utc)
       at or after t at the given location.

    """

    # start by finding a day who's event time happed before t
    date = t.date
    event_time = event(date, latitude, longitude)
    while t <= event_time:      # while t is at / before event on date
        date = date.yesterday() # step back one day
        event_time = event(date, latitude, longitude)

    # The time of event on 'date' is before t, now step forward and return the
    # first result where event is after t.
    
    while event_time < t:       # while event on date is before t 
        date = date.tomarrow()  # step forward one day
        event_time = event(date, latitude, longitude)

    return event_time

def time_of_last_before(event, t, latitude, longitude):
    """Return the time of the last event (a function like sunrise_utc)
       at or after t at the given location.
    """

    # start by finding a day who's event happend after t
    date = t.date
    event_time = event(date, latitude, longitude)
    while event_time <= t:       # while event on date is at / before t
        date = date.tomarrow()   # step forward one day
        event_time = event(date, latitude, longitude)

    # The time of event on 'date' is after t, now step back and return the
    # first result where event is before t.
    
    while t < event_time:        # while event on date is after t
        date = date.yesterday()  # step back one day
        event_time = event(date, latitude, longitude)

    return event_time

def sunrise_utc(date, latitude, longitude):
    """Calculate sunrise time in the UTC timezone.
    :param date:       Date to calculate for.
    :type date:        :class:`datetime.date`
    :param latitude:   Latitude - Northern latitudes should be positive
    :type latitude:    float
    :param longitude:  Longitude - Eastern longitudes should be positive
    :type longitude:   float
    :return: The UTC date and time (in seconds from midnight) at which sunrise occurs.
    """

    try:
        return _calc_time(90 + 0.833, SUN_RISING, date, latitude, longitude)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise AstralError(
                ("Sun never reaches the horizon on this day, " "at this location.")
            )
        else:
            raise

def sunset_utc(date, latitude, longitude):
    """Calculate sunset time in the UTC timezone.
    :param date:       Date to calculate for.
    :type date:        :class:`datetime.date`
    :param latitude:   Latitude - Northern latitudes should be positive
    :type latitude:    float
    :param longitude:  Longitude - Eastern longitudes should be positive
    :type longitude:   float
    :return: The UTC date and time (in seconds from midnight) at which sunrise occurs.
    """

    try:
        return _calc_time(90 + 0.833, SUN_SETTING, date, latitude, longitude)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise AstralError(
                ("Sun never reaches the horizon on this day, " "at this location.")
            )
        else:
            raise

def dusk_utc(date, latitude, longitude, depression='civil'):
    """Calculate dusk time in the UTC timezone.
    :param date:       Date to calculate for.
    :type date:        :class:`datetime.date`
    :param latitude:   Latitude - Northern latitudes should be positive
    :type latitude:    float
    :param longitude:  Longitude - Eastern longitudes should be positive
    :type longitude:   float
    :param depression: Override the depression used
    :type depression:   float
    :return: The UTC date and time (in seconds from midnight) at which sunrise occurs.
    """

    depression = _depression(depression)
    depression += 90

    try:
        return _calc_time(depression, SUN_SETTING, date, latitude, longitude)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise AstralError(
                (
                    "Sun never reaches %d degrees below the horizon, "
                    "at this location."
                )
                % (depression - 90)
            )
        else:
            raise

def dawn_utc(date, latitude, longitude, depression='civil'):
    """Calculate dawn time in the UTC timezone.
    :param date:       Date to calculate for.
    :type date:        :class:`datetime.date`
    :param latitude:   Latitude - Northern latitudes should be positive
    :type latitude:    float
    :param longitude:  Longitude - Eastern longitudes should be positive
    :type longitude:   float
    :param depression: Override the depression used
    :type depression:  float
    :return: The UTC date and time (in seconds from midnight) at which sunrise occurs.
    """

    depression = _depression(depression)
    depression += 90

    try:
        return _calc_time(depression, SUN_RISING, date, latitude, longitude)
    except ValueError as exc:
        if exc.args[0] == "math domain error":
            raise AstralError(
                (
                    "Sun never reaches %d degrees below the horizon, "
                    "at this location."
                )
                % (depression - 90)
            )
        else:
            raise


def _julianday(utc_date):
    start_date = Date(1900, 1, 1)
    date_diff = excel_datediff(start_date, utc_date)
    jd = date_diff + 2415018.5

    return jd

def _jday_to_jcentury(julianday):
    return (julianday - 2451545.0) / 36525.0

def _geom_mean_long_sun(juliancentury):
    l0 = 280.46646 + juliancentury * (36000.76983 + 0.0003032 * juliancentury)
    return l0 % 360.0

def _eccentrilocation_earth_orbit(juliancentury):
    return 0.016708634 - juliancentury * (
        0.000042037 + 0.0000001267 * juliancentury
    )

def _geom_mean_anomaly_sun(juliancentury):
    return 357.52911 + juliancentury * (35999.05029 - 0.0001537 * juliancentury)

def _mean_obliquity_of_ecliptic(juliancentury):
    seconds = 21.448 - juliancentury * (
        46.815 + juliancentury * (0.00059 - juliancentury * (0.001813))
    )
    return 23.0 + (26.0 + (seconds / 60.0)) / 60.0

def _obliquity_correction(juliancentury):
    e0 = _mean_obliquity_of_ecliptic(juliancentury)

    omega = 125.04 - 1934.136 * juliancentury
    return e0 + 0.00256 * cos(radians(omega))

def _var_y(juliancentury):
    epsilon = _obliquity_correction(juliancentury)
    y = tan(radians(epsilon) / 2.0)
    return y * y

def _eq_of_time(juliancentury):
    l0 = _geom_mean_long_sun(juliancentury)
    e = _eccentrilocation_earth_orbit(juliancentury)
    m = _geom_mean_anomaly_sun(juliancentury)

    y = _var_y(juliancentury)

    sin2l0 = sin(2.0 * radians(l0))
    sinm = sin(radians(m))
    cos2l0 = cos(2.0 * radians(l0))
    sin4l0 = sin(4.0 * radians(l0))
    sin2m = sin(2.0 * radians(m))

    Etime = (
        y * sin2l0
        - 2.0 * e * sinm
        + 4.0 * e * y * sinm * cos2l0
        - 0.5 * y * y * sin4l0
        - 1.25 * e * e * sin2m
    )

    return degrees(Etime) * 4.0

def _sun_eq_of_center(juliancentury):
    m = _geom_mean_anomaly_sun(juliancentury)

    mrad = radians(m)
    sinm = sin(mrad)
    sin2m = sin(mrad + mrad)
    sin3m = sin(mrad + mrad + mrad)

    c = (
        sinm * (1.914602 - juliancentury * (0.004817 + 0.000014 * juliancentury))
        + sin2m * (0.019993 - 0.000101 * juliancentury)
        + sin3m * 0.000289
    )

    return c

def _sun_true_long(juliancentury):
    l0 = _geom_mean_long_sun(juliancentury)
    c = _sun_eq_of_center(juliancentury)

    return l0 + c

def _sun_apparent_long(juliancentury):
    true_long = _sun_true_long(juliancentury)

    omega = 125.04 - 1934.136 * juliancentury
    return true_long - 0.00569 - 0.00478 * sin(radians(omega))

def _sun_declination(juliancentury):
    e = _obliquity_correction(juliancentury)
    lambd = _sun_apparent_long(juliancentury)

    sint = sin(radians(e)) * sin(radians(lambd))
    return degrees(asin(sint))

def _hour_angle(latitude, declination, depression):
    latitude_rad = radians(latitude)
    declination_rad = radians(declination)
    depression_rad = radians(depression)

    n = cos(depression_rad)
    d = cos(latitude_rad) * cos(declination_rad)
    t = tan(latitude_rad) * tan(declination_rad)
    h = (n / d) - t

    HA = acos(h)
    return HA

def _calc_time(depression, direction, date, latitude, longitude):
    t = _jday_to_jcentury(_julianday(date))
    eqtime = _eq_of_time(t)

    # Hack(?) to make solar_noon_utc work
    if (depression == 0):
        hourangle = 0
    else:
        if latitude > 89.8:
            latitude = 89.8

        if latitude < -89.8:
            latitude = -89.8

        solarDec = _sun_declination(t)
        hourangle = _hour_angle(latitude, solarDec, depression)

        if direction == SUN_SETTING:
            hourangle = -hourangle

    delta = -longitude - degrees(hourangle)
    timeDiff = 4.0 * delta # minutes
    timeUTC = 720.0 + timeDiff - eqtime # minutes

    return DateSeconds(date, int(timeUTC * 60))

