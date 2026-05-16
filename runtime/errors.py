#!/usr/bin/env python3
class TraceValidationError(Exception):
    pass

class ReplayCorruptionError(Exception):
    pass

class LifecycleOrderingError(Exception):
    pass

class NDJSONIntegrityError(TraceValidationError):
    pass
