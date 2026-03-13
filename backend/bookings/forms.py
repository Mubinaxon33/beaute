from django import forms

from salons.models import Employee, Service

from .models import Booking


class BookingCreateForm(forms.ModelForm):
    def __init__(self, *args, salon=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.salon = salon
        self.fields["employee"].required = True

        if salon:
            self.fields["service"].queryset = Service.objects.filter(salon=salon)
            self.fields["employee"].queryset = Employee.objects.filter(salon=salon, is_active=True)

    class Meta:
        model = Booking
        fields = ["service", "employee", "booking_date", "start_time", "notes"]

    def clean(self):
        cleaned_data = super().clean()
        service = cleaned_data.get("service")
        employee = cleaned_data.get("employee")

        if self.salon and service and service.salon_id != self.salon.id:
            self.add_error("service", "Selected service does not belong to this salon.")

        if self.salon and employee and employee.salon_id != self.salon.id:
            self.add_error("employee", "Selected specialist does not belong to this salon.")

        return cleaned_data


class BookingPageForm(forms.Form):
    service = forms.ModelChoiceField(queryset=Service.objects.select_related("salon"))
    employee = forms.ModelChoiceField(queryset=Employee.objects.select_related("salon"))
    booking_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    start_time = forms.TimeField(widget=forms.TimeInput(attrs={"type": "time"}))
    notes = forms.CharField(required=False, widget=forms.Textarea)
