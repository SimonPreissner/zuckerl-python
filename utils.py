#!/usr/bin/python3.6
#author: Simon Preissner

"""
This module provides helper functions.
"""

import sys
import re
from tqdm import tqdm
import time


def loop_input(rtype=str, default=None, msg=""):
    """
    Wrapper function for command-line input that specifies an input type
    and a default value. Input types can be string, int, float, or bool, 
    or "file", so that only existing files will pass the input.
    :param rtype: type of the input. one of str, int, float, bool, "file"
    :type rtype: type
    :param default: value to be returned if the input is empty
    :param msg: message that is printed as prompt
    :type msg: str
    :return: value of the specified type
    """
    while True:
        try:
            s = input(msg+f" (default: {default}): ")
            if rtype == bool and len(s) > 0:
                if s=="True":
                    return True
                elif s=="False":
                    return False
                else:
                    print("Input needs to be convertable to",rtype,"-- try again.")
                    continue
            if rtype == "file" and len(s)>0:
                try:
                    with open(s, "r"):
                        pass
                except FileNotFoundError as e:
                    print("File",s,"not found -- try again.")
                    continue
            else:
                return rtype(s) if len(s) > 0 else default
        except ValueError:
            print("Input needs to be convertable to",rtype,"-- try again.")
            continue


class ConfigReader():
    """
    Basic container and management of parameter configurations.
    Read a config file (typically ending with .cfg), use this as container for
    the parameters during runtime, and change/write parameters.

    CONFIGURATION FILE SYNTAX
    - one parameter per line, containing a name and a value
        - name and value are separated by at least one white space or tab
        - names should contain alphanumeric symbols and '_' (no '-', please!)
    - list-like values are allowed (use Python list syntax)
        - strings within value lists don't need to be quoted
        - value lists either with or without quotation (no ["foo", 3, "bar"] )
        - mixed lists will exclude non-quoted elements
    - multi-word expressions are marked with single or double quotation marks
    - TODO strings containing quotation marks are not tested yet. Be careful!
    - lines starting with '#' are ignored
    - no in-line comments!
    - config files should have the extension 'cfg' (to indicate their purpose)
    """

    def __init__(self, filepath):
        self.filepath = filepath
        self.params = self.read_config()

    def __repr__(self):
        """
        returns tab-separated key-value pairs (one pair per line)
        """
        return "\n".join([str(k)+"\t"+str(v) for k,v in self.params.items()])

    def __call__(self, *paramnames):
    """
    Returns a single value or a list of values corresponding to the
    provided parameter name(s). Returns the whole config in form of a
    dictionary if no parameter names are specified.
    """
    if not paramnames: # return the whole config
        return self.params
    else: # return specified values
        values = [self.params[name] for name in paramnames]
        if len(values) == 1:
            return values[0]
        else:
            return values

    def read_config(self):
        """
        Reads the ConfigReader's assigned file (attribute: 'filename') and parses
        the contents into a dictionary.
        - ignores empty lines and lines starting with '#'
        - takes the first continuous string as parameter key (or: parameter name)
        - parses all subsequent strings (splits at whitespaces) as values
        - tries to convert each value to float, int, and bool. Else: string.
        - parses strings that look like Python lists to lists
        :return: dict[str:obj]
        """
        cfg = {}
        with open(self.filepath, "r") as f:
            lines = f.readlines()

        for line in lines:
            line = line.rstrip()
            if not line: # ignore empty lines
                continue
            elif line.startswith('#'): # ignore comment lines
                continue

            words = line.split()
            paramname = words.pop(0)
            if not words: # no value specified
                print(f"WARNING: no value specified for parameter {paramname}.")
                paramvalue = None
            elif words[0].startswith("["): # detects a list of values
                paramvalue = self.listparse(" ".join(words))
            elif words[0].startswith('"') or words[0].startswith('\''): # detects a multi-word string
                paramvalue = self.stringparse(words)
            else:
                """ only single values are valid! """
                if len(words) > 1:
                    #TODO make this proper error handling (= throw an error)
                    print(f"ERROR while parsing {self.filepath} --",
                          f"too many values in line '{line}'.")
                    sys.exit()
                else:
                    """ parse the single value """
                    paramvalue = self.numberparse(words[0]) # 'words' is still a list
                    paramvalue = self.boolparse(paramvalue)

            cfg[paramname] = paramvalue # adds the parameter to the config

        self.config = cfg
        return self.config

    @classmethod
    def listparse(cls, liststring):
        """
        Parses a string that looks like a Python list (square brackets, comma
        separated, ...). A list of strings can make use of quotation marks, but
        doesn't need to. List-like strings that contain some quoted and some
        unquoted elements will be parsed to only return the quoted elements.
        Elements parsed from an unquoted list will be converted to numbers/bools
        if possible.
        Examples:
            [this, is, a, valid, list] --> ['this', 'is', 'a', 'valid', 'list']
            ["this", "one", "too"]     --> ['this', 'one', 'too']
            ['single', 'quotes', 'are', 'valid'] --> ['single', 'quotes', 'are', 'valid']
            ["mixing", 42, is, 'bad']  --> ['mixing', 'bad']
            ["54", "74", "90", "2014"] --> ['54', '74', '90', '2014']
            [54, 74, 90, 2014]         --> [54, 74, 90, 2014]
            [True, 1337, False, 666]   --> [True, 1337, False, 666]
            [True, 1337, "bla", False, 666] --> ['bla']
        """
        re_quoted = re.compile('["\'](.+?)["\'][,\]]')
        elements = re.findall(re_quoted, liststring)
        if elements:
            return elements

        re_unquoted = re.compile('[\[\s]*(.+?)[,\]]')
        elements = re.findall(re_unquoted, liststring)
        if elements:
            result = []
            for e in elements:
                e = cls.numberparse(e)  # convert to number if possible
                e = cls.boolparse(e)  # convert to bool if possible
                result.append(e)
            return result

    @staticmethod
    def stringparse(words):
        words[0] = words[0][1:] # delete opening quotation marks
        words[-1] = words[-1][:-1] #delete closing quotation marks
        return " ".join(words)

    @staticmethod
    def numberparse(string):
        """
        Tries to convert 'string' to a float or even int.
        Returns int/float if successful, or else the input string.
        """
        try:
            floaty = float(string)
            if int(floaty) == floaty:
                return int(floaty)
            else:
                return floaty
        except ValueError:
            return string

    @staticmethod
    def boolparse(string):
        if string == "True" or string == "False":
            return bool(string)
        else:
            return string

    def get_config(self):
        """
        returns the config as a dictionary
        """
        return self.params

    def get_params(self):
        """
        returns a list of parameter names
        """
        return [key for key in self.params.keys()]

    def get(self, *paramname):
        """
        returns a specific value or a tuple of values corresponding to the
        provided parameter name(s).
        """
        values = [self.params[name] for name in paramname]
        if len(values) == 1:
            return values[0]
        else:
            return tuple(values)

    def set(self, paramname, value):
        self.params.update({paramname:value})




class Timer():
    #TODO change data structure to contain the type of time-taking; e.g., (t1, t0, lap)
    #TODO change data structure to containe fragmented timing (multiple intervals)
    #TODO provide better documentation and usage instructions
    #TODO implement go_on()
    #TODO change total() to perform simple cumulative counting (no END_TIME)
    def __init__(self):
        self.START_TIME = time.time() 
        self.END_TIME = 0
        self.t0 = 0
        self.t_lap = 0
        self.counter = 0
        self.stopped_times = {}

    def __repr__(self):
        return "\n".join([str(round(t,6))+"   "+str(i) 
                          for i,t in self.stopped_times])

    def start(self):
        """ resets t0 (= reference time) to now """
        self.t0 = time.time()
        self.t_lap = self.t0
        return self.t0

    def stop(self, label=None):
        """ 
        Takes time since t0, without resetting t0. 
        Use this for cumulative timing. 
        """
        t1 = time.time()
        if not label: label = self.counter
        self.stopped_times[label] = (t1, self.t0)
        self.counter += 1
        return t1

    def go_on(self, label=None):
        """ 
        
        """
        t1 = time.time()
        if not label: label = self.counter
        self.stopped_times[label] = (t1, self.t0)
        self.counter += 1
        return t1

    def lap(self, label=None):
        """ 
        Takes time and resets t_lap to now. 
        Use this for subsequent intervals. 
        """
        t1 = time.time()
        if not label: label = self.counter
        self.stopped_times[label] = (t1, self.t_lap)
        self.counter += 1
        self.t_lap = t1
        return t1

    def total(self, label='total', ret_interval=True):
        """ 
        Like stop(), but takes time since initialization. 
        Use this to take total runtime.
        """
        self.END_TIME = time.time()
        interval = self.END_TIME - self.START_TIME
        self.stopped_times[label] = (self.END_TIME, self.START_TIME)
        if ret_interval:
            return interval
        else:
            return self.END_TIME

    def show(self, *labels, precision=4):
        """ returns particular times, identified by their labels """
        ret = ""
        for label in labels:
            t1, t0 = self.stopped_times[label]
            ret += (str(round(t1-t0, precision))+" "+str(label)+"\n")
        return ret.rstrip() # to get rid of the last newline

    def show_all(self, precision=4):
        """ shows all stored times with associated labels (or cardinal numbers if not specified) """
        ret = ""
        for label, (t1, t0) in self.stopped_times.items():
            ret += (str(round(t1-t0, precision))+" "+str(label)+"\n")
        return ret.rstrip() # to get rid of the last newline

