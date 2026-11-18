"""Base types."""

# Valid OSC types
type OscArg = int | float | str | bytes | bool | list[OscArg] | None
