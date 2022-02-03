from prompt_toolkit import PromptSession

import types

from prompt_toolkit.completion import Completion, Completer
class NestedCommandsFuzzyWordCompleter(Completer):
    def __init__(self, commands={}, completers={}):
        self.__sub_completers = completers
        self.__commands = commands

    def get_completions(self, document, complete_event):
        text_before_cursor = str(document.text_before_cursor)
        previous_words = text_before_cursor.split()

        current_state = self.__commands

        # Get to the current command node in commands dictionary.
        for word in previous_words:
            try:
                command = current_state.get(word)
            except:
                command = None

            if not command: break

            current_state = current_state.get(word)
            
        # Getting the completer provided by the client (in case he provided one).
        chosen_completer = self.__sub_completers
        index_of_last_command = 0
        for word in previous_words:
            try:
                chosen_completer = chosen_completer[word]
                index_of_last_command += 1
            except: pass

        # Check if dedicated completer was provided by the user
        # if not use the commands dictionary.
        # Client provided completer take precedent over the commands dictionary.
        if chosen_completer != None and isinstance(chosen_completer, Completer):

            # Generate the relevant document for dedicated completer.
            relevant_text = " ".join(document.text_before_cursor.split()[index_of_last_command:])
            relevant_document = Document(text=relevant_text)

            # Using the completer provided by the client
            yield from (Completion(completion.text, completion.start_position, display=completion.display)
                        for completion
                        in chosen_completer.get_completions(relevant_document, complete_event))
            # return chosen_completer.get_completions(relevant_document, complete_event)

        # Using the command node to get next commands
        else:
            try:
                for complete_word in list(current_state.keys()):
                    word = document.get_word_before_cursor()

                    if complete_word.startswith(word):
                        yield Completion(complete_word, start_position=-len(word))
            except: return

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

        try:
            codeOut = StringIO()
            codeErr = StringIO()

            sys.stdout = codeOut
            sys.stderr = codeErr

            fn(vapp, commands)

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
        else:
            print(output)

    return wrapper

class Vimapp:
    def __init__(self, name, commands):
        self.name = name
        self.commands = commands

        # adding base commands
        commands['exit'] = None
        commands['clear'] = None

        commands_completer = NestedCommandsFuzzyWordCompleter(self.commands, None)
        self.session = PromptSession(vi_mode=True,
                                        # reserve_space_for_menu=2,
                                        completer=commands_completer)

        # _fix_unecessary_blank_lines(self.session)

    def __root_command_handler(self, command):
        commands = command.split()

        if len(commands) == 0: return True
        if commands[0] == "exit": return False
        if commands[0] == "clear": 
            # TODO: clean the screen
            print('\033c')
            return True
            
        try:
            curr_state = self.commands

            for c in commands:
                if not isinstance(curr_state, types.FunctionType):
                    curr_state = curr_state[c]

            fn = command_handler(curr_state)
            fn(self, commands)

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

