# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: CloudletControl.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='CloudletControl.proto',
  package='',
  syntax='proto3',
  serialized_options=None,
  serialized_pb=_b('\n\x15\x43loudletControl.proto\"\x07\n\x05\x45mpty2V\n\x0f\x43loudletControl\x12!\n\x0fstartODLauncher\x12\x06.Empty\x1a\x06.Empty\x12 \n\x0estopODLauncher\x12\x06.Empty\x1a\x06.Emptyb\x06proto3')
)




_EMPTY = _descriptor.Descriptor(
  name='Empty',
  full_name='Empty',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=25,
  serialized_end=32,
)

DESCRIPTOR.message_types_by_name['Empty'] = _EMPTY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

Empty = _reflection.GeneratedProtocolMessageType('Empty', (_message.Message,), dict(
  DESCRIPTOR = _EMPTY,
  __module__ = 'CloudletControl_pb2'
  # @@protoc_insertion_point(class_scope:Empty)
  ))
_sym_db.RegisterMessage(Empty)



_CLOUDLETCONTROL = _descriptor.ServiceDescriptor(
  name='CloudletControl',
  full_name='CloudletControl',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=34,
  serialized_end=120,
  methods=[
  _descriptor.MethodDescriptor(
    name='startODLauncher',
    full_name='CloudletControl.startODLauncher',
    index=0,
    containing_service=None,
    input_type=_EMPTY,
    output_type=_EMPTY,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='stopODLauncher',
    full_name='CloudletControl.stopODLauncher',
    index=1,
    containing_service=None,
    input_type=_EMPTY,
    output_type=_EMPTY,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_CLOUDLETCONTROL)

DESCRIPTOR.services_by_name['CloudletControl'] = _CLOUDLETCONTROL

# @@protoc_insertion_point(module_scope)