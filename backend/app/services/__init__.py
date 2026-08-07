from app.services.auth_service import create_access_token, create_default_admin
from app.services.category_service import (
    create_category,
    delete_category,
    get_categories,
    get_category_by_id,
    update_category,
)
from app.services.reply_service import create_reply, get_replies_by_ticket
from app.services.ticket_service import (
    can_transition,
    create_ticket,
    generate_ticket_no,
    get_ticket_by_id,
    get_tickets_query,
    transition_ticket_status,
    update_ticket,
)
