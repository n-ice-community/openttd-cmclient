import re
from pathlib import Path
from pprint import pprint

RX_COMMAND = re.compile(r'(?P<returns>CommandCost|std::tuple<CommandCost, [^>]*>) (?P<name>Cmd\w*)\((?P<args>[^)]*)\);')
RX_ARG = re.compile(r'(?P<type>(:?const |)[\w:]* &?)(?P<name>\w*)')
RX_CAMEL_TO_SNAKE = re.compile(r'(?<!^)(?=[A-Z])')

FILES = [
    'src/misc_cmd.h',
    'src/object_cmd.h',
    'src/order_cmd.h',
    'src/town_cmd.h',
]

BASE_DIR = Path(__file__).parent
OUTPUT = BASE_DIR / 'src/citymania/generated/cm_gen_commands'


def parse_commands():
    res = []
    for f in FILES:
        for returns, name, args_str in RX_COMMAND.findall(open(BASE_DIR / f).read()):
            if returns.startswith('std::tuple'):
                ret_type = returns[24: -1]
            else:
                ret_type = None
            args = [RX_ARG.fullmatch(x).group('type', 'name') for x in args_str.split(', ')]
            args = args[1:]
            if args[0][0].strip() == 'TileIndex':
                args = args[1:]
            print(name, args)
            res.append((ret_type, name[3:], args))
    return res


def run():
    commands = parse_commands()
    with open(OUTPUT.with_suffix('.hpp'), 'w') as f:
        f.write(
            '// This file is generated by gen_commands.py, do not edit\n\n'
            '#ifndef CM_GEN_COMMANDS_HPP\n'
            '#define CM_GEN_COMMANDS_HPP\n'
            '#include "../cm_command_type.hpp"\n'
            'namespace citymania {\n'
            'namespace cmd {\n\n'
        )
        for rt, name, args in commands:
            args_list = ', '.join(f'{at} {an}' for at, an in args)
            args_init = ', '.join(f'{an}{{{an}}}' for _, an in args)
            f.write(
                f'class {name}: public Command {{\n'
                f'public:\n'
            )
            for at, an in args:
                f.write(f'    {at}{an};\n')
            f.write(
                f'\n'
                f'    {name}({args_list})\n'
                f'        :{args_init} {{}}\n'
                f'    ~{name}() override {{}}\n'
                f'\n'
                f'    bool DoPost() override;\n'
                f'}};\n\n'
            )
        f.write(
            '}  // namespace cmd\n'
            '}  // namespace citymania\n'
            '#endif\n'
        )

    with open(OUTPUT.with_suffix('.cpp'), 'w') as f:
        f.write(
            '// This file is generated by gen_commands.py, do not edit\n\n'
            '#include "../../stdafx.h"\n'
            '#include "cm_gen_commands.hpp"\n'
        )
        for fn in FILES:
            f.write(f'#include "../../{fn}"\n')
        f.write(
            'namespace citymania {\n'
            'namespace cmd {\n\n'
        )
        for rt, name, args in commands:
            constant = 'CMD_' + RX_CAMEL_TO_SNAKE.sub('_', name).upper()
            args_list = ', '.join(f'this->{an}' for _, an in args)
            f.write(
                f'bool {name}::DoPost() {{\n'
                f'    return ::Command<{constant}>::Post(this->error, this->tile, {args_list});\n'
                '}\n'
            )
            f.write('\n')
        f.write(
            '}  // namespace cmd\n'
            '}  // namespace citymania\n'
        )

if __name__ == "__main__":
    run()
