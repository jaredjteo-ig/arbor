"""Domain specialist agents for the HR advisory pipeline.

The specialist agents have been replaced by the Delegate engine, which
handles all advisory domains via tools.  Only utility classes remain:

  - _KaizenCompatMixin  (SDK 2.3.1 compatibility shim)
  - BaseDomainSpecialist (base class used by DocumentGenerationAgent)
  - DocumentGenerationSignature (from signatures.py)
"""

__all__: list[str] = []
