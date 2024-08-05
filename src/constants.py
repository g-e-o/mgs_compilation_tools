''' Constants '''
from enum import Enum

DEFAULT_PROCEDURE_PREFIX = 'sub'

#-------------------------------------------------------------------------------
# RADIO (radio.dat file)

class RadioCode(Enum):
    ''' Radio opcodes '''
    RD_NULL =         0
    TALK =            1
    VOICE =           2
    ANIM =            3
    ADD_CONTACT =     4
    MEMSAVE =         5
    SOUND =           6
    PROMPT =          7
    VARSAVE =         8
    IF =              0x10
    ELSE =            0x11
    ELSEIF =          0x12
    SWITCH =          0x20
    SWITCH_CASE =     0x21
    SWITCH_DEFAULT =  0x22
    RANDSWITCH =      0x30
    RANDSWITCH_CASE = 0x31
    EVAL =            0x40
    RD_SCRIPT =       0x80
    ENDLINE =         0xFF

#-------------------------------------------------------------------------------
# GCL (*.gcx files)

class GclCode(Enum):
    ''' GCL opcodes '''
    GCL_NULL = 0
    WORD =     1
    BYTE =     2
    CHAR =     3
    FLAG =     4
    STR_ID =   6
    STR =      7
    PROC =     8
    SD_CODE =  9
    TABLE =    10
    VAR =      0x10
    ARG =      0x20
    EXPR =     0x30
    OP =       0x31
    SCRIPT =   0x40
    OPTION =   0x50
    CMD =      0x60
    CALL =     0x70

class GclOperator(Enum):
    ''' GCL operators '''
    OP_NULL =            0
    # Single operand
    NEGATE =             1
    ISFALSE =            2
    COMPLEMENT =         3
    # Double operands
    ADD =                4
    SUBTRACT =           5
    MULTIPLY =           6
    DIVIDE =             7
    MODULUS =            8
    EQUALS =             9
    NOTEQUALS =          10
    LESSTHAN =           11
    LESSTHANOREQUAL =    12
    GREATERTHAN =        13
    GREATERTHANOREQUAL = 14
    BITWISEOR =          15
    BITWISEAND =         16
    BITWISEXOR =         17
    OR =                 18
    AND =                19
    ASSIGN =             20

OPERATOR_TYPES = {
    # Single operand
    GclOperator.NEGATE.name:             '-',
    GclOperator.ISFALSE.name:            '!',
    GclOperator.COMPLEMENT.name:         '~',
    # Double operands
    GclOperator.ADD.name:                '+',
    GclOperator.SUBTRACT.name:           '-',
    GclOperator.MULTIPLY.name:           '*',
    GclOperator.DIVIDE.name:             '/',
    GclOperator.MODULUS.name:            '%',
    GclOperator.EQUALS.name:             '==',
    GclOperator.NOTEQUALS.name:          '!=',
    GclOperator.LESSTHAN.name:           '<',
    GclOperator.LESSTHANOREQUAL.name:    '<=',
    GclOperator.GREATERTHAN.name:        '>',
    GclOperator.GREATERTHANOREQUAL.name: '>=',
    GclOperator.BITWISEOR.name:          '|',
    GclOperator.BITWISEAND.name:         '&',
    GclOperator.BITWISEXOR.name:         '^',
    GclOperator.OR.name:                 '||',
    GclOperator.AND.name:                '&&',
    GclOperator.ASSIGN.name:             '=',
}

#-------------------------------------------------------------------------------

class GclCommands(Enum):
    ''' GCL commands '''
    # Keywords commands
    IF =        0x0d86
    EVAL =      0x64c0
    RETURN =    0xcd3a
    FOREACH =   0x7636
    # Regular commands
    MESG =      0x22ff
    TRAP =      0xd4cb
    CHARA =     0x9906
    MAP =       0xc091
    MAPDEF =    0x7d50
    CAMERA =    0xeee9
    LIGHT =     0x306a
    START =     0x9a1f
    LOAD =      0xc8bb
    RADIO =     0x24e1
    RESTART =   0xe43c
    DEMO =      0xa242
    NTRAP =     0xdbab
    DELAY =     0x430d
    PAD =       0xcc85
    VARSAVE =   0x5c9e
    SYSTEM =    0x4ad9
    SOUND =     0x698d
    MENU =      0x226d
    RAND =      0x925e
    FUNC =      0xe257 # not sure!
    DEMODEBUG = 0xa2bf
    PRINT =     0xb96e
    JIMAKU =    0xec9d # "subtitle"
