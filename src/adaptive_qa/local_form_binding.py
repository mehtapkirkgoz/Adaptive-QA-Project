"""Reusable, non-executing form bindings restricted to owned loopback fixtures."""
from dataclasses import asdict, dataclass
import hashlib
import json
import re

from adaptive_qa.interactive_contracts import FormOperation, InteractiveFormContract

_ORIGIN = 'http://127.0.0.1:8000'


def _name(value):
    if not isinstance(value,str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_]{0,39}',value):
        raise ValueError('A bounded ASCII field name is required.')


def _url(value):
    if (not isinstance(value,str) or not 1<=len(value)<=256 or not value.startswith(_ORIGIN+'/')
            or not re.fullmatch(r'/[A-Za-z0-9/_-]*',value[len(_ORIGIN):])
            or '//' in value[len(_ORIGIN):]):
        raise ValueError('An exact normalized owned local path is required.')


def _unique(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('Duplicate response fields.')
        result[key]=value
    return result


@dataclass(frozen=True)
class LocalBooleanResponse:
    status_code: int
    field_name: str
    expected_value: bool

    def __post_init__(self):
        _name(self.field_name)
        if type(self.status_code) is not int or not (200<=self.status_code<=299 or 400<=self.status_code<=499):
            raise ValueError('A non-redirect response status is required.')
        if type(self.expected_value) is not bool:
            raise ValueError('Only a typed boolean response assertion is supported.')


@dataclass(frozen=True)
class LocalFormBinding:
    form: InteractiveFormContract
    document_url: str
    endpoint_url: str
    field_names: tuple[str,...]
    accepted: LocalBooleanResponse
    rejected: LocalBooleanResponse

    def __post_init__(self):
        if not isinstance(self.form,InteractiveFormContract):raise ValueError('A typed form contract is required.')
        _url(self.document_url);_url(self.endpoint_url)
        if self.document_url==self.endpoint_url:raise ValueError('Document and endpoint must be distinct.')
        count=2 if self.form.operation==FormOperation.LOGIN else 1
        if type(self.field_names) is not tuple or len(self.field_names)!=count:
            raise ValueError('Explicit operation-specific field names are required.')
        for name in self.field_names:_name(name)
        if len(set(self.field_names))!=count:raise ValueError('Distinct input fields are required.')
        if (not isinstance(self.accepted,LocalBooleanResponse) or not isinstance(self.rejected,LocalBooleanResponse)
                or self.accepted==self.rejected):
            raise ValueError('Distinct explicit positive and negative responses are required.')

    @property
    def method(self):return 'POST'

    @property
    def max_body_bytes(self):return 8192

    def validate_project(self,project,*,current_fingerprint):
        self.form.validate_project(project,current_fingerprint=current_fingerprint)
        if project.base_url!=self.document_url or project.allowed_hosts!=('127.0.0.1',):
            raise ValueError('Binding must match the exact owned project document.')

    def fingerprint(self):
        payload=dict(version=1,form=self.form.fingerprint(),document=self.document_url,endpoint=self.endpoint_url,
            fields=self.field_names,accepted=asdict(self.accepted),rejected=asdict(self.rejected),
            method=self.method,max_body_bytes=self.max_body_bytes,max_submissions=1,redirects=False,
            content_types=('application/x-www-form-urlencoded','application/x-www-form-urlencoded;charset=UTF-8'))
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()

    def classify_response(self,status,raw):
        if type(raw) is not bytes or len(raw)>1024:return None
        try:
            data=json.loads(raw.decode('utf-8'),object_pairs_hook=_unique)
            if not isinstance(data,dict) or len(data)!=1:return None
            for outcome,binding in (('accepted',self.accepted),('rejected',self.rejected)):
                if (status==binding.status_code and set(data)=={binding.field_name}
                        and type(data[binding.field_name]) is bool and data[binding.field_name] is binding.expected_value):
                    return outcome
        except (ValueError,UnicodeError,RecursionError):pass
        return None


def encode_local_binding(binding):
    if not isinstance(binding,LocalFormBinding):raise ValueError('A typed local binding is required.')
    data=asdict(binding);data.pop('form')
    return data


def decode_local_binding(data,form):
    if (not isinstance(data,dict) or set(data)!={'document_url','endpoint_url','field_names','accepted','rejected'}
            or not isinstance(data['field_names'],list)):
        raise ValueError('Exact local binding metadata is required.')
    responses=[]
    for key in ('accepted','rejected'):
        value=data[key]
        if not isinstance(value,dict) or set(value)!=set(LocalBooleanResponse.__dataclass_fields__):
            raise ValueError('Exact boolean response fields are required.')
        responses.append(LocalBooleanResponse(**value))
    return LocalFormBinding(form,data['document_url'],data['endpoint_url'],tuple(data['field_names']),*responses)
