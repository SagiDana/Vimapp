# from .completers import NestedCommandsFuzzyWordCompleter, PythonRuntimeCompleter
# from .snippets import modify_object_method
# from .source_inspecter import inspect_code
# from .lexers import PythonLexer
# from .containers import TabbedBuffersContainer, Session, Tab, TabsToolbar

# from prompt_toolkit.key_binding.bindings.focus import focus_next, focus_previous
from prompt_toolkit.layout.containers import VSplit, HSplit, Window
# from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.controls import BufferControl
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.layout import FloatContainer, Float
# from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.layout.layout import Layout
# from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.widgets import TextArea
# from prompt_toolkit.widgets import Frame
from prompt_toolkit.buffer import Buffer
from prompt_toolkit import Application


# from pygments.lexers.python import PythonLexer as PygmentsPythonLexer
# from prompt_toolkit.formatted_text import PygmentsTokens
# from pygments.token import Token
# import pygments
# import inspect
import types

# from os.path import isfile, join, splitext
# from os import listdir
# from sys import path
# import importlib

from prompt_toolkit.completion import Completion, Completer
from prompt_toolkit.document import Document

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

class Vimapp:
    def __configure_layout(self):
        # Configure completers used by the application.
        commands_completer = NestedCommandsFuzzyWordCompleter(self.commands, None)

        # # Configure PythonRuntimeCompleter
        # python_runtime_completer = PythonRuntimeCompleter(self)

        # --------- This is the CLI input container ---------
        # Comfigure the input container and handler.
        self.input_container = TextArea(prompt='{}> '.format(self.name),
                                   style='class:input-field',
                                   multiline=False,
                                   wrap_lines=True,
                                   completer=commands_completer,
                                   history=InMemoryHistory())
        self.input_container.accept_handler = lambda command: self.__root_command_handler(self.input_container.text)


        # Configure the output buffer to 'print' out results.
        self.output_buffer = Buffer()

        # --------- This is the Output container ---------
        self.output_container = Window(content=BufferControl(buffer=self.output_buffer), wrap_lines=True)

        # self.session = Session()
        # self.session.add_tab(Tab("Console", self.output_container))
        # self.session.add_tab(Tab("Python Interpreter Environment", self.python_code_container))

        # self.tabs_container = TabbedBuffersContainer(self.session)
        # self.tabs_container.set_selected_tab(0)

        # Configure the application layout.
        root_container = HSplit([
            VSplit([
                # Window for python code.
                self.output_container,
            ]),
            # Seperation line.
            Window(height=1,
                   char='-',
                   style='class:line'),
            # Command line prompt.
            self.input_container,
        ])
        
        self.floating_container = FloatContainer(content=root_container,floats=[
            Float(xcursor=True,
                  ycursor=True,
                  content=CompletionsMenu(max_height=16, scroll_offset=1))
        ])

        self.body_layout = Layout(self.floating_container)

    def __init__(self, name, commands):
        self.name = name
        self.commands = commands

        self.__configure_layout()

        # Creating the application.
        self.app = Application(layout=self.body_layout,
                               full_screen=True,
                               editing_mode=EditingMode.VI)

        # Focus on command line
        self.app.layout.focus(self.input_container)

    def __send_to_output(self, message):
        new_text = self.output_buffer.text + "{}\n".format(message)
        self.output_buffer.document = Document(text=new_text, cursor_position=len(new_text))

    def __root_command_handler(self, command):
        commands = command.split()

        if len(commands) == 0: return
            
        try:
            curr_state = self.commands

            for c in commands:
                if not isinstance(curr_state, types.FunctionType):
                    curr_state = curr_state[c]

            output = curr_state(self, commands)
            self.app.invalidate()

            self.__send_to_output(output)
        except Exception as e: 
            # print(f"[!] Exception: {e}")
            pass

    def run(self):
        self.app.run() # You won't be able to Exit this app
