"""This plugin provides test results in the standard XUnit XML format."""
import multiprocessing
import codecs
from datetime import datetime
from time import time

from nose.plugins.base import Plugin
from nose.plugins.xunit import Xunit, format_exception, id_split, nice_classname, exc_message, escape_cdata
from nose.pyversion import force_unicode
from nose.exc import SkipTest


class XunitMP(Xunit):
    """This plugin provides test results in the standard XUnit XML format."""

    name = 'xunitmp'
    score = 2000
    error_report_filename = None
    error_report_file = None

    def options(self, parser, env):
        """Sets additional command line options."""
        Plugin.options(self, parser, env)
        parser.add_option(
            '--xunitmp-file', action='store',
            dest='xunitmp_file', metavar="FILE",
            default=env.get('NOSE_XUNITMP_FILE', 'nosetests.xml'),
            help=("Path to xml file to store the xunit report in. "
                  "Default is nosetests.xml in the working directory "
                  "[NOSE_XUNIT_FILE]"))

    def configure(self, options, config):
        """Configures the xunit plugin."""
        Plugin.configure(self, options, config)
        self.config = config
        if self.enabled:
            # Each subprocess gets a new instance of this plugin. We need to be
            # sure that each of these instances shares the same errorlist/stats
            # Placing them on self.config achieves this, as nose pickles it and
            # passes it to each subprocess.
            # Doing it here (rather than at the module level) means that they
            # will be shared on Windows too.
            if not hasattr(self.config, '_nose_xunitmp_state'):
                manager = multiprocessing.Manager()
                self.errorlist = manager.list()
                self.stats = manager.dict(**{
                    'errors': 0,
                    'failures': 0,
                    'passes': 0,
                    'skipped': 0
                })
                self.config._nose_xunitmp_state = self.errorlist, self.stats
            else:
                self.errorlist, self.stats = self.config._nose_xunitmp_state
            self.error_report_filename = options.xunitmp_file

    def report(self, stream):
        """Writes an Xunit-formatted XML file

        The file includes a report of test errors and failures.

        """
        self.error_report_file = codecs.open(self.error_report_filename, 'w',
                                             self.encoding, 'replace')
        self.stats['encoding'] = self.encoding
        self.stats['total'] = (self.stats['errors'] + self.stats['failures']
                               + self.stats['passes'] + self.stats['skipped'])
        self.error_report_file.write(
            u'<?xml version="1.0" encoding="%(encoding)s"?>'
            u'<testsuite name="nosetests" tests="%(total)d" '
            u'errors="%(errors)d" failures="%(failures)d" '
            u'skip="%(skipped)d">' % self.stats)
        self.error_report_file.write(u''.join([
            force_unicode(error)
            for error
            in self.errorlist
        ]))

        self.error_report_file.write(u'</testsuite>')
        self.error_report_file.close()
        if self.config.verbosity > 1:
            stream.writeln("-" * 70)
            stream.writeln("XML: %s" % self.error_report_file.name)

    def addError(self, test, err, capt=None):
        """Add error output to Xunit report.
        """
        taken = self._timeTaken()

        if issubclass(err[0], SkipTest):
            type = 'skipped'
            self.stats['skipped'] += 1
        else:
            type = 'error'
            self.stats['errors'] += 1

        tb = format_exception(err, self.encoding)
        id = test.id()
        if hasattr(self, '_timer'):
            started = self._timer
        else:
            started = time()
        ended = started + taken

        self.errorlist.append(
            '<testcase classname=%(cls)s name=%(name)s time="%(taken).3f" started="%(started)s" ended="%(ended)s">'
            '<%(type)s type=%(errtype)s message=%(message)s><![CDATA[%(tb)s]]>'
            '</%(type)s>%(systemout)s%(systemerr)s</testcase>' %
            {'cls': self._quoteattr(id_split(id)[0]),
             'name': self._quoteattr(id_split(id)[-1]),
             'taken': taken,
             'type': type,
             'errtype': self._quoteattr(nice_classname(err[0])),
             'message': self._quoteattr(exc_message(err)),
             'tb': escape_cdata(tb),
             'systemout': self._getCapturedStdout(),
             'systemerr': self._getCapturedStderr(),
             'started': datetime.fromtimestamp(started).strftime('%x %X'),
             'ended': datetime.fromtimestamp(ended).strftime('%x %X'),
             })

    def addFailure(self, test, err, capt=None, tb_info=None):
        """Add failure output to Xunit report.
        """
        taken = self._timeTaken()
        tb = format_exception(err, self.encoding)
        self.stats['failures'] += 1
        id = test.id()
        if hasattr(self, '_timer'):
            started = self._timer
        else:
            started = time()
        ended = started + taken

        self.errorlist.append(
            '<testcase classname=%(cls)s name=%(name)s time="%(taken).3f" started="%(started)s" ended="%(ended)s">'
            '<failure type=%(errtype)s message=%(message)s><![CDATA[%(tb)s]]>'
            '</failure>%(systemout)s%(systemerr)s</testcase>' %
            {'cls': self._quoteattr(id_split(id)[0]),
             'name': self._quoteattr(id_split(id)[-1]),
             'taken': taken,
             'errtype': self._quoteattr(nice_classname(err[0])),
             'message': self._quoteattr(exc_message(err)),
             'tb': escape_cdata(tb),
             'systemout': self._getCapturedStdout(),
             'systemerr': self._getCapturedStderr(),
             'started': datetime.fromtimestamp(started).strftime('%x %X'),
             'ended': datetime.fromtimestamp(ended).strftime('%x %X'),
             })

    def addSuccess(self, test, capt=None):
        """Add success output to Xunit report.
        """
        taken = self._timeTaken()
        self.stats['passes'] += 1
        id = test.id()
        if hasattr(self, '_timer'):
            started = self._timer
        else:
            started = time()
        ended = started + taken
        self.errorlist.append(
            '<testcase classname=%(cls)s name=%(name)s '
            'time="%(taken).3f" started="%(started)s" ended="%(ended)s">%(systemout)s%(systemerr)s</testcase>' %
            {'cls': self._quoteattr(id_split(id)[0]),
             'name': self._quoteattr(id_split(id)[-1]),
             'taken': taken,
             'systemout': self._getCapturedStdout(),
             'systemerr': self._getCapturedStderr(),
             'started': datetime.fromtimestamp(started).strftime('%x %X'),
             'ended': datetime.fromtimestamp(ended).strftime('%x %X'),
             })
