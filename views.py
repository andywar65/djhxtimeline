from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from project.views import HxOnlyTemplateMixin, HxPageTemplateMixin

from .forms import PhaseCreateForm
from .models import Phase, get_month_dict, get_position_by_parent, move_younger_siblings


class RefreshListMixin:
    """Triggers the refresh list event that holds state"""

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response["HX-Trigger-After-Swap"] = "refreshList"
        return response


class PhaseListView(HxPageTemplateMixin, ListView):
    """Rendered in #content"""

    model = Phase
    template_name = "timeline/htmx/list.html"

    def get_queryset(self):
        qs = super(PhaseListView, self).get_queryset()
        qs = qs.with_tree_fields()
        return qs

    def get_context_data(self, **kwargs):
        context = super(PhaseListView, self).get_context_data()
        context["year"] = self.kwargs["year"]
        context["month"] = self.kwargs["month"]
        context["month_dict"] = get_month_dict(context["year"], context["month"])
        return context


class PhaseCreateView(HxOnlyTemplateMixin, CreateView):
    """Rendered in and redirects to #add_button"""

    model = Phase
    form_class = PhaseCreateForm
    template_name = "timeline/htmx/create.html"

    def form_valid(self, form):
        form.instance.position = get_position_by_parent(form.instance.parent)
        report = _("Added phase '%(title)s'") % {"title": form.instance.title}
        messages.success(self.request, report)
        return super(PhaseCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse("timeline:add_button") + "?refresh=true"


class PhaseAddButtonView(HxOnlyTemplateMixin, TemplateView):
    """Rendered in #add_button, may trigger refresh list"""

    template_name = "timeline/htmx/add_button.html"

    def dispatch(self, request, *args, **kwargs):
        response = super(PhaseAddButtonView, self).dispatch(request, *args, **kwargs)
        if "refresh" in request.GET:
            response["HX-Trigger-After-Swap"] = "refreshList"
        return response


class PhaseDetailView(HxOnlyTemplateMixin, DetailView):
    """Rendered in #phase-index-{{ self.id }}, may trigger refresh list"""

    model = Phase
    context_object_name = "phase"
    template_name = "timeline/htmx/detail.html"

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        if "refresh" in request.GET:
            response["HX-Trigger-After-Swap"] = "refreshList"
        return response


class PhaseUpdateView(HxOnlyTemplateMixin, UpdateView):
    """Rendered in and redirects to #phase-index-{{ self.id }}"""

    model = Phase
    form_class = PhaseCreateForm
    template_name = "timeline/htmx/update.html"

    def setup(self, request, *args, **kwargs):
        super(PhaseUpdateView, self).setup(request, *args, **kwargs)
        self.original_parent = None

    def get_object(self, queryset=None):
        obj = super(PhaseUpdateView, self).get_object(queryset=None)
        self.original_parent = obj.parent
        return obj

    def form_valid(self, form):
        if not self.original_parent == form.instance.parent:
            move_younger_siblings(self.original_parent, form.instance.position)
            form.instance.position = get_position_by_parent(form.instance.parent)
        return super(PhaseUpdateView, self).form_valid(form)

    def get_success_url(self, *args, **kwargs):
        return (
            reverse("timeline:detail", kwargs={"pk": self.object.id}) + "?refresh=true"
        )


class PhaseDeleteView(HxOnlyTemplateMixin, RefreshListMixin, TemplateView):
    """Rendered in #phase-index-{{ self.id }}, triggers refresh list"""

    template_name = "timeline/htmx/delete.html"

    def setup(self, request, *args, **kwargs):
        super(PhaseDeleteView, self).setup(request, *args, **kwargs)
        phase = get_object_or_404(Phase, id=self.kwargs["pk"])
        report = _("Deleted phase '%(title)s'") % {"title": phase.title}
        messages.error(request, report)
        move_younger_siblings(phase.parent, phase.position)
        phase.delete()


class PhaseMoveDownView(HxOnlyTemplateMixin, RefreshListMixin, TemplateView):
    """Rendered in #phase-index-{{ self.id }}, triggers refresh list"""

    template_name = "timeline/htmx/move.html"

    def setup(self, request, *args, **kwargs):
        super(PhaseMoveDownView, self).setup(request, *args, **kwargs)
        self.object = get_object_or_404(Phase, id=self.kwargs["pk"])
        self.object.move_down()


class PhaseMoveUpView(HxOnlyTemplateMixin, RefreshListMixin, TemplateView):
    """Rendered in #phase-index-{{ self.id }}, triggers refresh list"""

    template_name = "timeline/htmx/move.html"

    def setup(self, request, *args, **kwargs):
        super(PhaseMoveUpView, self).setup(request, *args, **kwargs)
        self.object = get_object_or_404(Phase, id=self.kwargs["pk"])
        self.object.move_up()
