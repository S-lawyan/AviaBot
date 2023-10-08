
class TicketsError(Exception):
    pass

class TicketApiConnectionError(TicketsError): #TicketsError
    pass

class TicketsAPIError(TicketsError):
    """Request for some reason was invalid"""
    pass

class TicketsParsingError(TicketsError):
    pass

class DatabaseAddTicketError(Exception):
    pass

class DatabaseUpdateTicketError(Exception):
    pass

class DatabaseUpdateDirectionSentPostsError(Exception):
    pass
