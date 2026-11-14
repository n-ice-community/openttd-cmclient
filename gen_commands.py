import glob
import json
import re
from pathlib import Path
from pprint import pprint

RX_COMMAND = re.compile(r'(?P<returns>CommandCost|std::tuple<CommandCost, [^>]*>) (?P<name>Cmd\w*)\((?P<args>[^)]*)\);')
RX_DEF_TRAIT = re.compile(r'DEF_CMD_TRAIT\(Commands::(?P<constant>\w+),\s+(?P<function>\w+),\s+(?P<flags>[^,()]+(?:\([^)]+\))?),\s+(?P<category>[\w:]+)\)')
RX_ARG = re.compile(r'(?P<type>(:?const |)[\w:]* &?)(?P<name>\w*)')
RX_CALLBACK = re.compile(r'void\s+(?P<name>Cc\w+)\(Commands')
RX_CALLBACK_REF = re.compile(r'CommandCallback(?:Data|)\s+(?P<name>Cc\w+);')
RX_CAMEL_TO_SNAKE = re.compile(r'(?<!^)(?=[A-Z])')
RX_CMD_CONSTANT = re.compile(r'^\s*\w+')

FILES = [
    'misc_cmd.h',
    'object_cmd.h',
    'order_cmd.h',
    'rail_cmd.h',
    'road_cmd.h',
    'station_cmd.h',
    'town_cmd.h',
    'tunnelbridge_cmd.h',
    'script/script_cmd.h',
]

BASE_CLASS = {
    'BuildDock': 'StationBuildCommand',
    'BuildRailStation': 'StationBuildCommand',
    'BuildAirport': 'StationBuildCommand',
    'BuildRoadStop': 'StationBuildCommand',
}

BASE_FIELDS = {
    'StationBuildCommand': ['station_to_join', 'adjacent'],
}

BASE_DIR = Path(__file__).parent
OUTPUT = BASE_DIR / 'src/citymania/generated/cm_gen_commands'
GLOBAL_TYPES = set(('GoalType', 'GoalTypeID', 'GoalID'))

TYPE_CONVERT = {
    'const std::string &': 'std::string',
}

AREA_CODE = {
    ('Commands::BuildRailStation',): (
        'if (this->axis == AXIS_X) return CommandArea(this->tile, this->plat_len, this->numtracks);\n'
        'return CommandArea(this->tile, this->numtracks, this->plat_len);\n'
    ),
    ('Commands::BuildRailAirport',): (
        'const AirportSpec *as = AirportSpec::Get(this->airport_type);\n'
        'if (!as->IsAvailable()) return CommandArea(this->tile);\n'
        'return CommandArea(this->tile, as->size_x, as->size_y);\n'
    ),
    ('Commands::BuildRoadStop',):
        'return CommandArea(this->tile, this->width, this->length);\n',
    #TODO diagonal areas
    (
        'Commands::PlantTree',
        'Commands::BuildRailLong',
        'Commands::RemoveRailLong',
        'Commands::BuildRoadLong',
        'Commands::RemoveRoadLong',
        'Commands::ClearArea',
        'Commands::BuildCanal',
        'Commands::LevelLand',
        'Commands::BuildBridge',
    ): 'return CommandArea(this->start_tile, this->tile);\n',
    (
        'Commands::BuildBridge',
    ): 'return CommandArea(this->tile_start, this->tile);\n',
    (
        'Commands::BuildRail',
        'Commands::BuildRailDepot',
        'Commands::BuildBuoy',
        'Commands::BuildRoad',
        'Commands::BuildRoadDepot',
        'Commands::PlaceSign',
        'Commands::LandscapeClear',
        'Commands::TerraformLand',
        'Commands::FoundTown',  # TODO
        'Commands::BuildDock',  # TODO
        'Commands::BuildShipDepot',  # TODO
        'Commands::BuildLock',  # TODO
        'Commands::BuildObject',  # TODO
        'Commands::BuildIndustry',  # TODO
        'Commands::BuildTunnel',  # TODO find other end
    ): 'return CommandArea(this->tile);\n'
}

DEFAULT_AREA_CODE = 'return CommandArea();\n'

def parse_commands():
    res = []
    includes = []
    callbacks = []

    command_ids = {}
    cid = 0
    dec_line_found = False
    for line in open(BASE_DIR / 'src' / 'command_type.h'):
        if not dec_line_found and "enum class Commands" in line:
            dec_line_found = True
            continue
        elif not dec_line_found:
            continue

        if "}" in line:
            break

        cl = RX_CMD_CONSTANT.findall(line)
        if not cl:
            continue
        cmd = cl[0].strip()
        command_ids[cmd] = cid
        cid += 1

    for f in glob.glob(str(BASE_DIR / 'src' / '*_cmd.h')) + glob.glob(str(BASE_DIR / 'src' / '*' / '*_cmd.h')):
    # for f in glob.glob(str(BASE_DIR / 'src' / 'group_cmd.h')):
        includes.append(Path(f).name)
        data = open(f).read()
        traits = {}
        for constant, name, flags, category in RX_DEF_TRAIT.findall(data):
            traits[name] = constant, flags, category
        callbacks.extend(RX_CALLBACK.findall(data))
        callbacks.extend(RX_CALLBACK_REF.findall(data))
        for returns, name, args_str in RX_COMMAND.findall(data):
            trait = traits.get(name)
            if not trait:
                print(f'Not a command: {name}')
                continue
            print(f, name, end=' ', flush=True)
            constant, flags, category = trait
            cid = command_ids[constant]
            if returns.startswith('std::tuple'):
                result_type = returns[24: -1]
                if result_type in GLOBAL_TYPES:
                    result_type = '::' + result_type
            else:
                result_type = None
            args = [RX_ARG.fullmatch(x).group('type', 'name') for x in args_str.split(', ')]
            args = args[1:]  # flags
            for i, (at, an) in enumerate(args):
                at = at.strip()
                if at in GLOBAL_TYPES:
                    at = '::' + at
                args[i] = (at, an)
            do_args = args[:]
            if 'Location' in flags:
                args = [('TileIndex', 'location')] + args
            print(cid, constant, category, args)
            callback_args = 'CommandCost' if result_type is None else f'CommandCost, {result_type}'
            callback_type = f'std::function<void ({callback_args})>'
            area_code = DEFAULT_AREA_CODE
            for cl, cc in AREA_CODE.items():
                if constant in cl:
                    area_code = cc

            default_run_as = 'INVALID_COMPANY'
            if 'Deity' in flags:
                default_run_as = 'OWNER_DEITY'
            if 'Server' in flags or 'Spectator' in flags:
                default_run_as = 'COMPANY_SPECTATOR'  # same as INVALID though

            res.append({
                'name': name[3:],
                'id': cid,
                'constant': constant,
                'category': category,
                'flags': flags,
                'default_run_as': default_run_as,
                'args': args,
                'do_args': do_args,
                'returns': returns,
                'result_type': result_type,
                'callback_type': callback_type,
                'area_code': area_code,
            })
    return res, includes, callbacks

CPP_TEMPLATES = '''\
inline constexpr size_t _callback_tuple_size = std::tuple_size_v<decltype(_callback_tuple)>;

#ifdef SILENCE_GCC_FUNCTION_POINTER_CAST
#   pragma GCC diagnostic push
#   pragma GCC diagnostic ignored "-Wcast-function-type"
#endif

template <size_t... i>
inline auto MakeCallbackTable(std::index_sequence<i...>) noexcept {
    return std::array<::CommandCallback *, sizeof...(i)>{{ reinterpret_cast<::CommandCallback *>(reinterpret_cast<void(*)()>(std::get<i>(_callback_tuple)))... }}; // MingW64 fails linking when casting a pointer to its own type. To work around, cast it to some other type first.
}
/** Type-erased table of callbacks. */
static auto _callback_table = MakeCallbackTable(std::make_index_sequence<_callback_tuple_size>{});\n
template <typename T> struct CallbackArgsHelper;
template <typename... Targs>
struct CallbackArgsHelper<void(*const)(Commands, const CommandCost &, Targs...)> {
    using Args = std::tuple<std::decay_t<Targs>...>;
};
#ifdef SILENCE_GCC_FUNCTION_POINTER_CAST
#   pragma GCC diagnostic pop
#endif

static size_t FindCallbackIndex(::CommandCallback *callback) {
    if (auto it = std::ranges::find(_callback_table, callback); it != std::end(_callback_table)) {
        return static_cast<size_t>(std::distance(std::begin(_callback_table), it));
    }
    return std::numeric_limits<size_t>::max();
}

template <Commands Tcmd, size_t Tcb, typename... Targs>
bool _DoPost(StringID err_msg, Targs... args) {
    return ::Command<Tcmd>::Post(err_msg, std::get<Tcb>(_callback_tuple), std::forward<Targs>(args)...);
}
template <Commands Tcmd, size_t Tcb, typename... Targs>
constexpr auto MakeCallback() noexcept {
    /* Check if the callback matches with the command arguments. If not, don''t generate an Unpack proc. */
    using Tcallback = std::tuple_element_t<Tcb, decltype(_callback_tuple)>;
    if constexpr (std::is_same_v<Tcallback, ::CommandCallback * const> ||
            std::is_same_v<Tcallback, CommandCallbackData * const> ||
            std::is_same_v<typename CommandTraits<Tcmd>::CbArgs, typename CallbackArgsHelper<Tcallback>::Args> ||
            (!std::is_void_v<typename CommandTraits<Tcmd>::RetTypes> && std::is_same_v<typename CallbackArgsHelper<typename CommandTraits<Tcmd>::RetCallbackProc const>::Args, typename CallbackArgsHelper<Tcallback>::Args>)) {
        return &_DoPost<Tcmd, Tcb, Targs...>;
    } else {
        return nullptr;
    }
}

template <Commands Tcmd, typename... Targs, size_t... i>
inline constexpr auto MakeDispatchTableHelper(std::index_sequence<i...>) noexcept
{
    return std::array<bool (*)(StringID err_msg, Targs...), sizeof...(i)>{MakeCallback<Tcmd, i, Targs...>()... };
}

template <Commands Tcmd, typename... Targs>
inline constexpr auto MakeDispatchTable() noexcept
{
    return MakeDispatchTableHelper<Tcmd, Targs...>(std::make_index_sequence<_callback_tuple_size>{});
}

'''

def run():
    commands, includes, callbacks = parse_commands()
    json.dump({
        'commands': commands,
        'includes': includes,
        'callbacks': callbacks,
    }, open('commands.json', 'w'))
    with open(OUTPUT.with_suffix('.hpp'), 'w') as f:
        f.write(
            '// This file is generated by gen_commands.py, do not edit\n\n'
            '#ifndef CM_GEN_COMMANDS_HPP\n'
            '#define CM_GEN_COMMANDS_HPP\n'
            '#include "../cm_command_type.hpp"\n'
        )
        for i in includes:
            f.write(f'#include "../../{i}"\n')
        f.write('\n')
        f.write(
            'namespace citymania {\n'
            'namespace cmd {\n\n'
        )
        for cmd in commands:
            name = cmd['name']
            base_class = BASE_CLASS.get(name, 'Command')
            base_fields = BASE_FIELDS.get(base_class, [])
            f.write(
                f'class {name}: public {base_class} {{\n'
                f'public:\n'
            )
            args_list = ', '.join(f'{at} {an}' for at, an in cmd['args'])
            args_init = ', '.join(f'{an}{{{an}}}' for _, an in cmd['args'] if an not in base_fields)
            if base_fields:
                base_joined = ', '.join(base_fields)
                args_init = f'{base_class}{{{base_joined}}}, ' + args_init
            for at, an in cmd['args']:
                if an in base_fields:
                    continue
                f.write(f'    {at} {an};\n')
            f.write(f'\n')
            if args_init:
                f.write(
                    f'    {name}({args_list})\n'
                    f'        :{args_init} {{}}\n'
                )
            else:
                f.write(f'    {name}({args_list}) {{}}\n')

            f.write(
                f'    ~{name}() override {{}}\n'
                f'\n'
                f'    bool _post(::CommandCallback * callback) override;\n'
                f'    CommandCost _do(DoCommandFlags flags) override;\n'
                f'    Commands get_command() override;\n'
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
        f.write(
            '/*\n'
            ' * The code is mostly copied from network_command.cpp\n'
            ' * but the table is not the same.\n'
            ' */\n'
            'static constexpr auto _callback_tuple = std::make_tuple(\n'
            '    (::CommandCallback *)nullptr, // Make sure this is actually a pointer-to-function.\n'
        )
        for i, cb in enumerate(callbacks):
            comma = ',' if i != len(callbacks) - 1 else ''
            f.write(f'    &{cb}{comma}\n')
        f.write(');\n\n')
        f.write(CPP_TEMPLATES)

        for cmd in commands:
            name = cmd['name']
            constant = cmd['constant']
            this_args_list = ', '.join(f'this->{an}' for _, an in cmd['args'])
            args_list = ', '.join(f'{an}' for _, an in cmd['args'])
            args_type_list = ', '.join(f'{at}' for at, an in cmd['args'])
            test_args_list = ', '.join(f'{an}' for _, an in cmd['do_args'])
            cost_getter = '' if cmd['result_type'] is None else 'std::get<0>'
            sep_args_list = sep_args_type_list = sep_this_args_list = ''
            if args_list:
                sep_args_list = ', ' + args_list
                sep_args_type_list = ', ' + args_type_list
                sep_this_args_list = ', ' + this_args_list
            f.write(
                f'Commands {name}::get_command() {{ return Commands::{constant}; }}\n'
                    f'static constexpr auto _{name}_dispatch = MakeDispatchTable<Commands::{constant}{sep_args_type_list}>();\n'
                f'bool {name}::_post(::CommandCallback *callback) {{\n'
                f'    return _{name}_dispatch[FindCallbackIndex(callback)](this->error{sep_this_args_list});\n'
                '}\n'
                f'CommandCost {name}::_do(DoCommandFlags flags) {{\n'
                f'    return {cost_getter}(::Command<Commands::{constant}>::Do(flags, {test_args_list}));\n'
                '}\n'
            )
            f.write('\n')
        f.write(
            '}  // namespace cmd\n'
            '}  // namespace citymania\n'
        )

if __name__ == "__main__":
    run()
