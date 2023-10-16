class TicketsError(Exception):
    pass


class TicketApiConnectionError(TicketsError):  # TicketsError
    pass


class TicketsAPIError(TicketsError):
    """Request for some reason was invalid"""


class InternalError(Exception):
    pass


class TicketsParsingError(InternalError):
    pass


class MissingTicketsError(InternalError):
    pass


class DatabaseAddTicketError(Exception):
    pass


class DatabaseUpdateTicketError(Exception):
    pass


class DatabaseGetTicketError(Exception):
    pass


class DatabaseUpdateDirectionSentPostsError(Exception):
    pass


class AddNewTicket(Exception):
    pass
