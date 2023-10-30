from __future__ import annotations

from typing import Any, Callable, Literal, NewType

NodeId = NewType("NodeId", str)
InputId = NewType("InputId", int)
OutputId = NewType("OutputId", int)


RunFn = Callable[..., Any]

NodeType = Literal["regularNode", "newIterator", "collector"]
