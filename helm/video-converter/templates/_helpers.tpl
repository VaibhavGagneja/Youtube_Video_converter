{{/*
Common labels
*/}}
{{- define "video-converter.labels" -}}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/instance: {{ .Release.Name }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{/*
Selector labels for a component
*/}}
{{- define "video-converter.selectorLabels" -}}
app.kubernetes.io/name: {{ .name }}
app.kubernetes.io/instance: {{ .release }}
{{- end }}

{{/*
Full image name
*/}}
{{- define "video-converter.image" -}}
{{ .global.image.repository }}/{{ .image.name }}:{{ .global.image.tag }}
{{- end }}
