from django.contrib import admin
from .models import (
    BotConfig, ProjectSubscription, Document, DocumentChunk, Lead, PendingLead,
    ConversationLog, TelegramAccountConnection, TelegramGroup,
)


@admin.register(BotConfig)
class BotConfigAdmin(admin.ModelAdmin):
    list_display = ("business_name", "ai_enabled", "updated_at")


@admin.register(ProjectSubscription)
class ProjectSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("is_active", "subscription_end", "updated_at")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "chunk_count", "created_at")
    list_filter = ("status",)


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "order")
    search_fields = ("content",)


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("full_name", "channel", "telegram_username", "phone", "status", "created_at")
    list_filter = ("status", "channel")


@admin.register(PendingLead)
class PendingLeadAdmin(admin.ModelAdmin):
    list_display = ("telegram_user_id", "step", "full_name", "created_at")


@admin.register(ConversationLog)
class ConversationLogAdmin(admin.ModelAdmin):
    list_display = ("telegram_user_id", "channel", "question", "answered_by_ai", "created_at")
    list_filter = ("channel",)


@admin.register(TelegramAccountConnection)
class TelegramAccountConnectionAdmin(admin.ModelAdmin):
    list_display = ("status", "phone_number", "connected_username", "connected_at")


@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = ("title", "chat_id", "is_ai_enabled", "reply_mode", "sender_filter", "last_seen_at")
    list_filter = ("is_ai_enabled", "reply_mode", "sender_filter")
