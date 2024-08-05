'''Handle gcx data'''
import sys
import struct

class GcxData(bytearray):
    ''' GCX bytecode buffer '''

    offset: int

    def __init__(self, *arg, **kw):
        self.offset = 0
        if len(arg) > 0 and isinstance(arg[0], str):
            super(GcxData, self).__init__()
            self.load_gcx_file(arg[0])
        else:
            super(GcxData, self).__init__(*arg, **kw)

    def load_gcx_file(self, gcx_file):
        ''' Read a GCX file into buffer '''
        try:
            with open( gcx_file, 'rb' ) as f:
                self[:] = f.read()
        except OSError as err:
            print( 'Error reading gcx file:', err )
            sys.exit(1)

    #---------------------------------------------------------------------------
    # Read buffer

    def read_byte(self, offset=None):
        ''' Read 1 byte value '''
        if offset is not None:
            value = self[offset]
        else:
            value = self[self.offset]
            self.offset += 1
        return value

    def read_short(self, offset=None):
        ''' Read 2 bytes value '''
        if offset is not None:
            value = struct.unpack_from( '>H', self, offset )[0]
        else:
            value = struct.unpack_from( '>H', self, self.offset )[0]
            self.offset += 2
        return value

    def read_int(self, offset=None):
        ''' Read 4 bytes value '''
        if offset is not None:
            value = struct.unpack_from( '>I', self, offset )[0]
        else:
            value = struct.unpack_from( '>I', self, self.offset )[0]
            self.offset += 4
        return value

    def read_string(self, length=0, fonts=[]):
        ''' Read string '''

        s = ''
        length = 0xff
        for i in range( length - 1 ):
            if self.read_byte( self.offset ) == 0:
                break
            try:
                letter = chr( self.read_byte() )
            except UnicodeEncodeError:
                letter = '\\x%02X' % self.read_byte( self.offset - 1 )
            s += letter
        self.read_byte()
        return s

    def read_hex_string(self, length):
        ''' Read bytes to hex string '''
        s = ''
        for _ in range( length ):
            s += '%02x' % self.read_byte()
        return s

    #---------------------------------------------------------------------------
    # Write buffer

    def push_byte(self, value):
        ''' Append byte value to buffer '''
        self.append( value & 0xff )

    def push_short(self, value):
        ''' Append short value to buffer '''
        self.extend( value.to_bytes(length=2, byteorder='big') )

    def push_int(self, value):
        ''' Append integer value to buffer '''
        self.extend( value.to_bytes(length=4, byteorder='big') )

    def push_hex_string(self, value):
        ''' Append hex string value to buffer '''
        for i in range( int( len(value) / 2 ) ):
            self.push_byte( int( value[i*2:i*2+2], 16 ) )

    def push_string(self, value):
        ''' Append string value to buffer '''

        self.extend( self.encode_string( value ) )

    def encode_string(self, value):
        ''' Encode string '''
        i = 0
        s = GcxData()
        while i < len(value):
            if value[i:].startswith( '\\x' ):
                letter = int( value[i+2:i+4], 16 )
                i += 4
            else:
                letter = ord( value[i] )
                i += 1
            s.push_byte( letter )
        s.push_byte( 0 )
        return s

class GclNode(dict):
    ''' GCL AST node '''

    def __init__(self, *arg, **kw):

        super(GclNode, self).__init__(*arg, **kw)

    def get(self):
        ''' Return (type, value) '''
        node_type: str = next( iter( self ) )
        node_value = self[node_type]
        return node_type, node_value

    def browse(self, callback, node=None):
        ''' Exec callback in every tree nodes  '''

        if node is None:
            node = self
        if 'PROC_DATA' in self:
            return self.browse( callback, node['PROC_DATA'] )
        if isinstance( node, list ):
            for child in node:
                self.browse( callback, child )
        elif isinstance( node, GclNode ):
            node_type, node_value = node.get()
            callback( node_type, node_value )
            if isinstance( node_value, GclNode ) or isinstance( node_value, list ):
                self.browse( callback, node_value )

class DatFile():
    ''' Handle files packed in .DAT files '''

    name: str
    _offset: int
    block_index: int
    data: GcxData

    def __init__(self, name: str, offset: int, data: GcxData) -> None:

        self.name = name
        self.offset = offset
        self.data = data

    @property
    def offset(self):
        return self._offset

    @offset.setter
    def offset(self, value):
        self._offset = value
        self.block_index = int( value / 0x800 )
