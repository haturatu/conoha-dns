package conoha

type Domain struct {
	UUID string `json:"uuid"`
	Name string `json:"name"`
}

type Record struct {
	UUID        string  `json:"uuid"`
	Name        string  `json:"name"`
	Type        string  `json:"type"`
	Data        string  `json:"data"`
	TTL         *int    `json:"ttl"`
	Description *string `json:"description"`
	Priority    *int    `json:"priority"`
	Weight      *int    `json:"weight"`
	Port        *int    `json:"port"`
}
