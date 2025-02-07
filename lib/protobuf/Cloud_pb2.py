# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: Cloud.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='Cloud.proto',
  package='jayx86service',
  syntax='proto3',
  serialized_options=_b('\n\035pt.up.fc.dcc.hyrax.jay.protocB\nx86JayGRPC'),
  serialized_pb=_b('\n\x0b\x43loud.proto\x12\rjayx86service\"\x1a\n\tBoolValue\x12\r\n\x05value\x18\x01 \x01(\x08\"\x07\n\x05\x45mpty\"\x15\n\x06String\x12\x0b\n\x03str\x18\x01 \x01(\t2\xcd\x01\n\x0fLauncherService\x12?\n\x0bStartWorker\x12\x14.jayx86service.Empty\x1a\x18.jayx86service.BoolValue\"\x00\x12\x38\n\x04Stop\x12\x14.jayx86service.Empty\x1a\x18.jayx86service.BoolValue\"\x00\x12?\n\nSetLogName\x12\x15.jayx86service.String\x1a\x18.jayx86service.BoolValue\"\x00\x42+\n\x1dpt.up.fc.dcc.hyrax.jay.protocB\nx86JayGRPCb\x06proto3')
)




_BOOLVALUE = _descriptor.Descriptor(
  name='BoolValue',
  full_name='jayx86service.BoolValue',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='value', full_name='jayx86service.BoolValue.value', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
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
  serialized_start=30,
  serialized_end=56,
)


_EMPTY = _descriptor.Descriptor(
  name='Empty',
  full_name='jayx86service.Empty',
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
  serialized_start=58,
  serialized_end=65,
)


_STRING = _descriptor.Descriptor(
  name='String',
  full_name='jayx86service.String',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='str', full_name='jayx86service.String.str', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR),
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
  serialized_start=67,
  serialized_end=88,
)

DESCRIPTOR.message_types_by_name['BoolValue'] = _BOOLVALUE
DESCRIPTOR.message_types_by_name['Empty'] = _EMPTY
DESCRIPTOR.message_types_by_name['String'] = _STRING
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

BoolValue = _reflection.GeneratedProtocolMessageType('BoolValue', (_message.Message,), dict(
  DESCRIPTOR = _BOOLVALUE,
  __module__ = 'Cloud_pb2'
  # @@protoc_insertion_point(class_scope:jayx86service.BoolValue)
  ))
_sym_db.RegisterMessage(BoolValue)

Empty = _reflection.GeneratedProtocolMessageType('Empty', (_message.Message,), dict(
  DESCRIPTOR = _EMPTY,
  __module__ = 'Cloud_pb2'
  # @@protoc_insertion_point(class_scope:jayx86service.Empty)
  ))
_sym_db.RegisterMessage(Empty)

String = _reflection.GeneratedProtocolMessageType('String', (_message.Message,), dict(
  DESCRIPTOR = _STRING,
  __module__ = 'Cloud_pb2'
  # @@protoc_insertion_point(class_scope:jayx86service.String)
  ))
_sym_db.RegisterMessage(String)


DESCRIPTOR._options = None

_LAUNCHERSERVICE = _descriptor.ServiceDescriptor(
  name='LauncherService',
  full_name='jayx86service.LauncherService',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  serialized_start=91,
  serialized_end=296,
  methods=[
  _descriptor.MethodDescriptor(
    name='StartWorker',
    full_name='jayx86service.LauncherService.StartWorker',
    index=0,
    containing_service=None,
    input_type=_EMPTY,
    output_type=_BOOLVALUE,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='Stop',
    full_name='jayx86service.LauncherService.Stop',
    index=1,
    containing_service=None,
    input_type=_EMPTY,
    output_type=_BOOLVALUE,
    serialized_options=None,
  ),
  _descriptor.MethodDescriptor(
    name='SetLogName',
    full_name='jayx86service.LauncherService.SetLogName',
    index=2,
    containing_service=None,
    input_type=_STRING,
    output_type=_BOOLVALUE,
    serialized_options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_LAUNCHERSERVICE)

DESCRIPTOR.services_by_name['LauncherService'] = _LAUNCHERSERVICE

# @@protoc_insertion_point(module_scope)
