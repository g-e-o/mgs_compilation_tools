''' Compile gcl script to gcx data '''
import sys

from gcx import GcxData
from constants import *

class GclComp:
    ''' Compile GCL script to GCX data '''

    gcx = GcxData()

    def __init__(self, radio=None, is_pc_version=False, vox_files=[], demo_files=[]) -> None:

        self.gcx = GcxData()
        self.radio = radio
        self.vox_files = vox_files
        self.demo_files = demo_files
        if is_pc_version:
            self.is_pc_version = True
        elif radio is not None:
            self.is_pc_version = radio.is_pc_version

    def compile_gcl_file(self, node):
        ''' Compile AST tree to GCX file '''

        data = GcxData()
        header = GcxData()
        procedures_data = GcxData()
        fonts_data = GcxData()

        for elem in node:
            if 'FONTS' in elem:
                for font in elem['FONTS']:
                    fonts_data.push_hex_string( font )
                continue
            proc_id = elem[ 'PROC_ID' ]
            proc_data = self.compile_gcl( elem[ 'PROC_DATA' ] )
            if proc_id == 0:
                data.push_short( proc_id )
                data.push_short( len( procedures_data ) + len( header ) + 4 )
                procedures_data.push_int( len( proc_data ) )
            else:
                header.push_short( proc_id )
                header.push_short( len( procedures_data ) )

            procedures_data.extend( proc_data )

        data.extend( header )
        data.push_int( 0 )
        data.extend( procedures_data )
        data.push_int( len( fonts_data ) )
        data.extend( fonts_data )

        if not self.is_pc_version:
            while len( data ) % 4 != 0:
                data.push_byte( 0 )

        self.gcx = data
        return data

    def compile_gcl(self, node):
        ''' Compile GCL AST to GCX data '''

        data = GcxData()

        if isinstance( node, list ):
            for child in node:
                data.extend( self.compile_gcl( child ) )
            return data

        gcl_code, value = node.get()

        match gcl_code:

            case GclCode.WORD.name:

                data.push_short( value )

            case GclCode.BYTE.name:

                data.push_byte( value )

            case GclCode.CHAR.name:

                data.push_byte( ord( value ) )

            case GclCode.FLAG.name:

                data.push_byte( value )

            case GclCode.STR_ID.name:

                data.push_short( value )

            case GclCode.STR.name:

                string = self.gcx.encode_string( value )
                data.push_byte( len( string ) )
                data.extend( string )

            case GclCode.PROC.name:

                data.push_short( value )

            case GclCode.SD_CODE.name:

                data.push_int( value )

            case GclCode.TABLE.name:

                if isinstance( value, str ):
                    # Resolve radio dialog file name.
                    if value.lower().startswith('rd_'):
                        if not value in self.radio.dialog_calls:
                            print('Error: could not resolve radio code', hex(value))
                            sys.exit(1)
                        value = int( self.radio.dialog_calls[ value ], 16 )
                    # Resolve voice file name
                    elif value.lower().startswith('vc'):
                        value = next((vox_file.block_index for vox_file in self.vox_files if vox_file.name == value), '')
                        if value == '':
                            print('Error: could not resolve voice code')
                            sys.exit(1)
                    # Resolve demo file name
                    elif value.lower().startswith('s'):
                        value = next((demo_file.block_index for demo_file in self.demo_files if demo_file.name == value), '')
                        if value == '':
                            print('Error: could not resolve demo code')
                            sys.exit(1)
                    else:
                        print('unexpected table value', hex(value))
                        sys.exit(1)

                data.push_int( value )

            case GclCode.VAR.name:

                var_type, var_value = value.get()
                data.push_byte( GclCode.VAR.value + GclCode[var_type].value )
                data.push_hex_string( var_value )
                return data

            case GclCode.ARG.name:

                data.push_byte( value )

            case GclCode.EXPR.name:

                expression = GcxData()
                for operator in value:
                    operation = self.compile_gcl( operator )
                    expression.extend( operation )
                expression.push_byte( GclCode.OP.value )
                expression.push_byte( 0 )

                data.push_byte( len( expression ) + 1 )
                data.extend( expression )

            case GclCode.OP.name:

                operator, operands = value.get()
                data.extend( self.compile_gcl( operands[0] ) )
                data.extend( self.compile_gcl( operands[1] ) )
                data.push_byte( GclCode.OP.value )
                data.push_byte( GclOperator[ operator ].value )
                return data

            case GclCode.SCRIPT.name:

                script = self.compile_gcl( value )
                script.push_byte( 0 )

                data.push_short( len( script ) + 2 )
                data.extend( script )

                if 'NO_BRACES' in node:
                    data = data[:-1]

            case GclCode.OPTION.name:

                option_letter, option_values = value.get()
                option_values = self.compile_gcl( option_values )

                data.push_byte( ord( option_letter ) )
                if 'NULL_SIZE' in value:
                    data.push_byte( 0 )
                else:
                    data.push_byte( len( option_values ) + 1 )
                data.extend( option_values )

            case GclCode.CMD.name:

                cmd_name, cmd_args = value.get()
                cmd_code = GclCommands[ cmd_name ].value

                command = GcxData()
                command.push_short( cmd_code )

                command_args = GcxData()
                for arg in cmd_args:
                    arg_type, arg_value = arg.get()
                    if arg_type == GclCode.OPTION.name:
                        break
                    argument = self.compile_gcl( arg )
                    command_args.extend( argument )

                args_size = len( command_args ) + 1

                # Patch 'if' size
                if cmd_name == GclCommands.IF.name and len( cmd_args ) == 2:
                    args_size += 1

                command_options = GcxData()
                for i, arg in enumerate( cmd_args ):
                    arg_type, arg_value = arg.get()
                    if arg_type != GclCode.OPTION.name:
                        continue
                    option = self.compile_gcl( arg )

                    # Patch 'elseif' and 'else' sizes
                    if cmd_name == GclCommands.IF.name:
                        opt_letter, opt_value = arg_value.get()
                        if opt_letter == 'i' and len(opt_value) == 2 and i == len(cmd_args) - 1:
                            option[2] += 1
                        elif opt_letter == 'e' and len(opt_value) == 1 and i == len(cmd_args) - 1:
                            option[2] += 1

                    command_options.extend( option )

                command.push_byte( args_size )
                command.extend( command_args )

                command.extend( command_options )
                command.push_byte( 0 )

                data.push_short( len( command ) + 2 )
                data.extend( command )

            case GclCode.CALL.name:

                procedure_id, procedure_args = value.get()

                call = GcxData()
                call.push_short( int( procedure_id ) )
                for arg in procedure_args:
                    call.extend( self.compile_gcl( arg ) )
                call.push_byte( 0 )

                data.push_byte( len( call ) + 1 )
                data.extend( call )

            case _:
                print('Unexpected code %s while compiling..' % gcl_code)
                sys.exit(1)

        data.insert( 0, GclCode[ gcl_code ].value )
        return data
