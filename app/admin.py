from sqladmin import Admin, ModelView, BaseView, expose
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse

from .models import Document, Tag
from .config import get_settings

class ApiKeyAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        api_key = form.get("username", "")  # Using username field for API key
        
        # Verify against your existing API key
        if api_key == get_settings().api_key:
            request.session.update({"api_key": api_key})
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        api_key = request.session.get("api_key")
        if not api_key:
            return False
        
        return api_key == get_settings().api_key

class DocumentAdmin(ModelView, model=Document):
    column_list = [Document.id, Document.title, Document.description, 
                  Document.interestingness, Document.created_at]
    column_searchable_list = [Document.title, Document.description, Document.content]
    column_sortable_list = [Document.id, Document.title, Document.interestingness, 
                          Document.created_at]
    column_filters = [Document.interestingness]
    can_create = True
    can_edit = True
    can_delete = True
    page_size = 20

class TagAdmin(ModelView, model=Tag):
    column_list = [Tag.id, Tag.name, Tag.description]
    column_searchable_list = [Tag.name, Tag.description]
    can_create = True
    can_edit = True
    can_delete = True

def setup_admin(app, engine):
    authentication_backend = ApiKeyAuth(secret_key="your-secret-key-here")
    admin = Admin(
        app,
        engine,
        authentication_backend=authentication_backend,
        title="Crumpet Admin"
    )
    
    admin.add_view(DocumentAdmin)
    admin.add_view(TagAdmin)
    
    return admin
