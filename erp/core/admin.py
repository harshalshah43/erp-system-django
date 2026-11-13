from django.contrib import admin, messages
from .models import Product, StockDocument, StockMove
from .services import StockError, reverse_document


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "stock_quantity", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("stock_quantity",)


class StockMoveInline(admin.TabularInline):
    model = StockMove
    fields = ("product", "quantity")
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StockDocument)
class StockDocumentAdmin(admin.ModelAdmin):
    """Read-only: documents are corrected by reversing them, never edited."""

    list_display = ("__str__", "kind", "note", "created_at", "created_by", "reversed_by")
    list_filter = ("kind",)
    inlines = [StockMoveInline]
    actions = ["reverse_selected"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Reverse selected documents")
    def reverse_selected(self, request, queryset):
        for doc in queryset:
            try:
                reversal = reverse_document(doc, user=request.user)
            except StockError as e:
                self.message_user(request, str(e), messages.ERROR)
            else:
                self.message_user(request, f"{doc} reversed by {reversal}.")
