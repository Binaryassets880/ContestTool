"""Custom exceptions for feed operations."""


class FeedError(Exception):
    """Base exception for feed-related errors."""
    pass


class FeedUnavailableError(FeedError):
    """Raised when the remote feed cannot be fetched."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class FeedParseError(FeedError):
    """Raised when feed data cannot be parsed."""
    pass
