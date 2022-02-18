from prompt_toolkit import PromptSession

from IPython import embed
import types

from prompt_toolkit.completion import Completion, Completer

class NestedCommandsFuzzyWordCompleter(Completer):
    def __init__(self, commands={}, completers={}):
        self.__completers = completers
        self.__commands = commands

    def get_completions(self, document, complete_event):
        text_before_cursor = str(document.text_before_cursor)
        previous_words = text_before_cursor.split()
        suggestions = []

        # First try using the completers

        # Getting the completer provided by the client (in case he provided one).
        chosen_completer = self.__completers
        index_of_last = 0
        for word in previous_words:
            try:
                chosen_completer = chosen_completer[word]
                index_of_last += 1
            except: 
                chosen_completer = None # do FALLBACK
        if chosen_completer:
            for complete_word in list(chosen_completer.keys()):
                word = document.get_word_before_cursor()

                if complete_word.startswith(word):
                    suggestions.append(complete_word)
                    # suggestions.append(Completion(  complete_word, 
                                                    # start_position=-len(word)))

        # Second try using the commands to get next commands
        current_state = self.__commands
        # Get to the current command node in commands dictionary.
        for word in previous_words:
            try:
                command = current_state.get(word)
            except:
                command = None

            if not command: break

            current_state = current_state.get(word)

        try:
            for complete_word in list(current_state.keys()):
                word = document.get_word_before_cursor()

                if complete_word.startswith(word):
                    suggestions.append(complete_word)
                    # suggestions.append(Completion(  complete_word, 
                                                    # start_position=-len(word)))
        except: pass

        # remove duplicates
        suggestions = set(suggestions)
        len_curr = len(document.get_word_before_cursor())
        for suggestion in suggestions:
            yield Completion(suggestion,
                             start_position=-len_curr)


def get_terminal_size():
    import os
    env = os.environ
    def ioctl_GWINSZ(fd):
        try:
            import fcntl, termios, struct, os
            cr = struct.unpack('hh', fcntl.ioctl(fd, termios.TIOCGWINSZ,
        '1234'))
        except:
            return
        return cr
    cr = ioctl_GWINSZ(0) or ioctl_GWINSZ(1) or ioctl_GWINSZ(2)
    if not cr:
        try:
            fd = os.open(os.ctermid(), os.O_RDONLY)
            cr = ioctl_GWINSZ(fd)
            os.close(fd)
        except:
            pass
    if not cr:
        cr = (env.get('LINES', 25), env.get('COLUMNS', 80))

        ### Use get(key[, default]) instead of a try/catch
        #try:
        #    cr = (env['LINES'], env['COLUMNS'])
        #except:
        #    cr = (25, 80)
    return int(cr[1]), int(cr[0])

import subprocess
import os
def command_handler(fn):
    (width, height) = get_terminal_size()
    def wrapper(vapp, commands):
        import sys
        from io import StringIO
        ret = True

        try:
            codeOut = StringIO()
            codeErr = StringIO()

            sys.stdout = codeOut
            sys.stderr = codeErr

            ret = fn(vapp, commands)

            # restore stdout and stderr
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

            # codeErr.getvalue()
            output = codeOut.getvalue()

            codeOut.close()
            codeErr.close()
        except Exception as e:
            output = str(e)

        if len(output.splitlines()) > height:
            with open('/tmp/vimapp_tmp', 'w+') as f:
                f.write(output)
            subprocess.call(['vim', '/tmp/vimapp_tmp'])
            os.remove('/tmp/vimapp_tmp')
        elif len(output.strip()) > 0:
            print(output)
        return ret

    return wrapper

class Vimapp:
    @staticmethod
    def embed_command_handler(vapp, commands):
        embed()
        return True

    @staticmethod
    def exit_command_handler(vapp, commands):
        return False

    @staticmethod
    def clear_command_handler(vapp, commands):
        import sys
        sys.stdout.write('\033c')
        return True

    def __add_base_commands(self):
        self.commands['exit'] = Vimapp.exit_command_handler
        self.commands['clear'] = Vimapp.clear_command_handler
        self.commands['embed'] = Vimapp.embed_command_handler

    def __init__(self, name, commands, completers=None):
        self.name = name
        self.commands = commands

        self.__add_base_commands()

        commands_completer = NestedCommandsFuzzyWordCompleter(  self.commands, 
                                                                completers)
        self.session = PromptSession(vi_mode=True,
                                        # reserve_space_for_menu=2,
                                        completer=commands_completer)

        # _fix_unecessary_blank_lines(self.session)

    def __root_command_handler(self, command):
        commands = command.split()

        if len(commands) == 0: return True
            
        try:
            curr_state = self.commands

            for c in commands:
                if not isinstance(curr_state, types.FunctionType):
                    curr_state = curr_state[c]

            fn = command_handler(curr_state)
            return fn(self, commands)

        except Exception as e: 
            print(f"Exception: {e}")
        return True

    def run(self):
        # self.app.run() # You won't be able to Exit this app
        while True:
            try:
                command = self.session.prompt(f"{self.name}> ")

                if not self.__root_command_handler(command): break

            except KeyboardInterrupt as e: break
            except Exception as e: print(f"Exception: {e}")

