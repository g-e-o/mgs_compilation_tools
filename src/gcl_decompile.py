''' Decompile gcx file to gcl code '''
import sys
import json
import textwrap

from gcx import GclNode, GcxData
from constants import *

class GclDecomp:
    ''' Decompile gcx file to gcl code '''

    tree_data = []
    procedures = []
    commands_stack = []

    def __init__(self, gcx: GcxData, radio=None, vox_files=[], demo_files=[]) -> None:

        self.gcx = gcx
        self.procedures = []
        self.tree_data = []
        self.commands_stack = []
        self.radio = radio
        self.vox_files = vox_files
        self.demo_files = demo_files

    def to_json(self, indent=None) -> str:
        ''' Return decompiled data in json format '''

        return json.dumps( self.tree_data, indent=indent )

    def to_gcl_script(self) -> str:
        ''' Return decompiled data in gcl script format '''

        gcl = ''
        for elem in self.tree_data:
            gcl += self.decomp_script( elem )
        return gcl

    def export_json(self, path='out.json', indent=None):
        ''' Export AST data to json file '''
        with open( path, 'w', encoding='utf-8' ) as f:
            f.write( json.dumps( self.tree_data, indent=indent ) )

    def decompile_gcx_file(self):
        ''' Decompile GCX file to AST data '''
        # Read procedures id's (that was hashed using GV_StrCode())
        #   and their relative offsets.
        while True:
            proc_id = self.gcx.read_short()
            proc_offset = self.gcx.read_short()
            if proc_id == 0 and proc_offset == 0:
                break
            self.procedures.append({
                'id':     proc_id,
                'offset': proc_offset
            })
        # Move main procedure at the end.
        self.procedures = self.procedures[1:] + self.procedures[:1]
        header_size = self.gcx.offset
        # Read procedures data.
        for proc in self.procedures:
            if proc['id'] == 0:
                self.gcx.offset = proc['offset'] + 8
            else:
                self.gcx.offset = proc['offset'] + header_size
            self.tree_data.append({
                'PROC_ID':   proc['id'],
                'PROC_DATA': self.decompile_gcx()
            })
        # Read fonts images data.
        fonts_size = self.gcx.read_int() - 2
        fonts_end = self.gcx.offset + fonts_size
        fonts = []
        while self.gcx.offset < fonts_end:
            font = self.gcx.read_hex_string( 36 )
            fonts.append( font )
        if len( fonts ) > 0:
            self.tree_data.append({
                'FONTS': fonts,
            })

    def current_command(self):
        ''' Get the current command during decompilation '''

        return self.commands_stack[-1:][0]

    def decompile_gcx(self):
        ''' Build json tree from gcx data '''

        gcl_code = self.gcx.read_byte()

        if gcl_code & 0xF0 == GclCode.VAR.value:

            variable = ''
            for _ in range(3):
                variable += '%02X' % self.gcx.read_byte()

            value = GclNode({ GclCode( gcl_code & 0xF ).name: variable })
            gcl_code = GclCode.VAR.value

        else:
            match gcl_code:

                case GclCode.GCL_NULL.value:
                    return None

                case GclCode.WORD.value:
                    value = self.gcx.read_short()

                case GclCode.BYTE.value:
                    value = self.gcx.read_byte()

                case GclCode.CHAR.value:
                    value = chr( self.gcx.read_byte() )

                case GclCode.FLAG.value:
                    value = self.gcx.read_byte() == 1

                case GclCode.STR_ID.value:
                    value = self.gcx.read_short()

                case GclCode.STR.value:

                    size = self.gcx.read_byte()
                    value = self.gcx.read_string( length=size )

                case GclCode.PROC.value:
                    value = self.gcx.read_short()

                case GclCode.SD_CODE.value:
                    value = self.gcx.read_int()

                case GclCode.TABLE.value:

                    value = self.gcx.read_int()
                    command = self.current_command()
                    # Resolve radio dialog file name from offset.
                    if command == GclCommands.RADIO.value and self.radio is not None:
                        dialog_index = ( value & 0xffff ) * 0x800
                        for dialog in self.radio.tree_data:
                            if dialog['DIALOG']['OFFSET'] == dialog_index:
                                value = dialog['DIALOG']['NAME']
                                break
                    # Resolve vox file name.
                    elif command == GclCommands.SOUND.value and len( self.vox_files ) > 0:
                        voice_name = next((vox_file.name for vox_file in self.vox_files if vox_file.block_index == value), '')
                        if voice_name == '':
                            print('Error: could not resolve voice code', hex(value))
                            sys.exit(1)
                        value = voice_name
                    # Resolve demo file name.
                    elif command == GclCommands.DEMO.value and len( self.demo_files ) > 0 and value != 0xffffffff:
                        demo_name = next((demo_file.name for demo_file in self.demo_files if demo_file.block_index == value), '')
                        if demo_name == '':
                            print('Error: could not resolve demo code', hex(value))
                            sys.exit(1)
                        value = demo_name

                case GclCode.ARG.value:

                    # Procedure argument index (on the stack)
                    value = self.gcx.read_byte()

                case GclCode.EXPR.value:

                    size = self.gcx.read_byte() - 1
                    end_offset = self.gcx.offset + size

                    operands = []
                    while self.gcx.offset < end_offset:
                        op = self.decompile_gcx()
                        op_type, op_value = op.get()
                        # Operator
                        if op_type == GclCode.OP.name:
                            if op_value == GclOperator.OP_NULL.name:
                                break
                            operation = GclNode({
                                op_type: GclNode({
                                    op_value: operands[-2:]
                                })
                            })
                            del operands[-2:]
                            operands.append( operation )
                        # Operand
                        else:
                            operands.append( op )

                    value = operands

                case GclCode.OP.value:

                    operator = self.gcx.read_byte()
                    value = GclOperator( operator ).name

                case GclCode.SCRIPT.value:

                    size = self.gcx.read_short() - 2
                    end_offset = self.gcx.offset + size

                    value = []
                    while self.gcx.offset < end_offset:
                        command_or_call = self.decompile_gcx()
                        if not command_or_call:
                            break
                        value.append( command_or_call )

                case GclCode.OPTION.value:

                    option_letter = chr( self.gcx.read_byte() )
                    size = self.gcx.read_byte() - 1
                    end_offset = self.gcx.offset + size

                    data = []
                    # Sadly we can't rely on size here so we have to check end byte...
                    while True:
                        code = self.gcx.read_byte( self.gcx.offset )
                        if not code or code == GclCode.OPTION.value:
                            break

                        option_offset = self.gcx.offset
                        val = self.decompile_gcx()
                        if not val:
                            break

                        # Checks if no braces "{}" were used in "elseif" or "else" declaration (my theory)
                        #   because it alters the size and we need this info for recompiling matching gcx..
                        opt_type, _ = val.get()
                        if self.current_command() == GclCommands.IF.value and opt_type == GclCode.SCRIPT.name:
                            script_size = self.gcx.read_short( option_offset + 1 )
                            if script_size + 2 - size == 1:
                                val['NO_BRACES'] = True

                        data.append( val )

                    value = GclNode({ option_letter: data })

                    # If data with null size, we need to save the info for the compiler as well..
                    if size == -1 and len(data) > 0:
                        value['NULL_SIZE'] = True

                case GclCode.CMD.value:

                    size = self.gcx.read_short() - 2
                    end_offset = self.gcx.offset + size

                    command_id = self.gcx.read_short()
                    self.commands_stack.append( command_id )

                    args_size = self.gcx.read_byte() - 1
                    args_end = self.gcx.offset + args_size
                    args = []
                    while True:
                        code = self.gcx.read_byte( self.gcx.offset )
                        if not code:
                            break
                        arg = self.decompile_gcx()
                        if not arg:
                            break
                        args.append( arg )

                    # Checks if no braces "{}" were used in "if" declaration
                    if command_id == GclCommands.IF.value and args_end - self.gcx.offset == 0:
                        args[1]['NO_BRACES'] = True

                    options = []
                    while self.gcx.offset < end_offset:
                        option = self.decompile_gcx()
                        if not option:
                            break
                        options.append( option )

                    value = GclNode({ GclCommands( command_id ).name: args + options })

                    self.commands_stack.pop()

                case GclCode.CALL.value:

                    size = self.gcx.read_byte() - 1
                    end_offset = self.gcx.offset + size
                    proc_id = str( self.gcx.read_short() )

                    proc_args = []
                    while self.gcx.offset < end_offset:
                        arg = self.decompile_gcx()
                        if not arg:
                            break
                        proc_args.append( arg )

                    value = GclNode({ proc_id: proc_args })

                case _:
                    print(f'Error: unexpected default case (GclCode: {gcl_code}, value: {value}, offset: {self.gcx.offset})')
                    sys.exit(1)

        return GclNode({ GclCode( gcl_code ).name: value })

    def indent_text(self, text) -> str:
        ''' Indent text block '''

        return textwrap.indent( text, 4 * ' ' )

    def decomp_script(self, node) -> str:
        ''' Convert json AST to GCL script '''

        s = ''

        if 'FONTS' in node:
            s += '#' + ('-' * 79) + '\n'
            s += '# Font glyphs\n\n'
            s += '['
            for i, font in enumerate( node['FONTS'] ):
                s += f'\n    "{font}"'
                if i != len( node['FONTS'] ):
                    s += ','
            s += '\n]\n'
            return s

        elif 'PROC_DATA' in node:
            if node['PROC_ID'] == 0:
                s += '#' + ('-' * 79) + '\n'
                s += '# Main procedure\n\n'

            # Browse procedure to find out how many arguments are used.
            self.max_arg_index = 0
            def check_arg( arg_type, arg_value ):
                if arg_type == GclCode.ARG.name and arg_value > self.max_arg_index:
                    self.max_arg_index = arg_value
            node['PROC_DATA'].browse( check_arg )

            args = ''
            for index in range( self.max_arg_index ):
                args += ' arg%d' % ( index+1 )
                if index+1 != self.max_arg_index:
                    args += ','
                else:
                    args += ' '

            s += 'proc %s_%04X(%s) ' % ( DEFAULT_PROCEDURE_PREFIX, node['PROC_ID'], args )
            s += self.decomp_script( node['PROC_DATA'] )
            s += '\n'
            return s

        node_type, value = node.get()

        match node_type:

            case GclCode.WORD.name:

                s += '%d' % value

            case GclCode.BYTE.name:

                s += 'b:%d' % value

            case GclCode.CHAR.name:

                s += "'%c'" % value

            case GclCode.FLAG.name:

                s += 'f:%r' % value

            case GclCode.STR_ID.name:

                s += 's:%04x' % value

            case GclCode.STR.name:

                s += '"%s"' % value

            case GclCode.PROC.name:

                s += '%s_%04X' % ( DEFAULT_PROCEDURE_PREFIX, value )

            case GclCode.SD_CODE.name:

                s += 'sd:%X' % value

            case GclCode.TABLE.name:

                if isinstance( value, str ):
                    s += 't:%s' % value
                else:
                    s += 't:%08X' % value

            case GclCode.VAR.name:

                var_type, var_value = value.get()
                s += '$%s:%s' % ( var_type[0].lower(), var_value )

            case GclCode.ARG.name:

                s += 'arg%d' % value

            case GclCode.EXPR.name:

                parentheses = False
                expression = ''
                for op in value:
                    expression += self.decomp_script( op )
                if len( value ) == 1 and not expression.startswith('('):
                    parentheses = True

                if parentheses:
                    s = f'( {expression} )'
                else:
                    s = expression

            case GclCode.OP.name:

                op_type, operands = value.get()
                operator = OPERATOR_TYPES[op_type]

                # Single operand operation
                if GclOperator[op_type].value < 4:
                    # @todo: remove first useless operand
                    s += operator + self.decomp_script( operands[1] )
                # Double operands operation
                else:
                    parentheses = False
                    op_type0, operands0 = operands[0].get()
                    op_type1, operands1 = operands[1].get()
                    if op_type != GclOperator.AND.name:
                        if op_type0 == GclCode.OP.name or op_type1 == GclCode.OP.name:
                            parentheses = True

                    if parentheses:
                        s += '( '
                    s += self.decomp_script( operands[0] )
                    s += ' ' + operator + ' '
                    s += self.decomp_script( operands[1] )
                    if parentheses:
                        s += ' )'

            case GclCode.SCRIPT.name:

                if not 'NO_BRACES' in node:
                    s += '{'
                s += '\n'
                for command_or_call in value:
                    s += self.indent_text( self.decomp_script( command_or_call ) )
                if not 'NO_BRACES' in node:
                    s += '}'
                s += '\n'

            case GclCode.OPTION.name:

                option_letter, option_args = value.get()
                s += '\n' + self.indent_text( '-' + option_letter )

                option_values = ''
                for arg in option_args:
                    option_values += ' ' + self.decomp_script( arg )

                s += self.indent_text( option_values )

            case GclCode.CMD.name:

                command_name, command_args = value.get()
                s += command_name.lower()

                for arg in command_args:

                    arg_type, arg_value = arg.get()
                    if command_name == GclCommands.IF.name and arg_type == GclCode.OPTION.name:
                        if_type, if_value = arg_value.get()
                        if if_type == 'i':
                            s = s[:-1] + ' elseif '
                            s += self.decomp_script( if_value[0] )
                            s += ' '
                            s += self.decomp_script( if_value[1] )
                        elif if_type == 'e':
                            s = s[:-1] + ' else '
                            s += self.decomp_script( if_value[0] )
                        continue
                    if command_name == GclCode.STR.name:
                        s += '\n'

                    end_spacing = ' '
                    if command_name == GclCommands.EVAL.name or arg_type == GclCode.OPTION.name:
                        end_spacing = ''
                    s += end_spacing + self.decomp_script( arg )

                s = s.strip() + '\n'

            case GclCode.CALL.name:

                proc_id, proc_args = value.get()
                s += f'call( {DEFAULT_PROCEDURE_PREFIX}_%04X' % int( proc_id )
                for proc_arg in proc_args:
                    s += ', ' + self.decomp_script( proc_arg )
                s += ' )\n'

            case _:
                print(f'Unexpected node type {node_type} while building script..')
                sys.exit(1)

        return s
