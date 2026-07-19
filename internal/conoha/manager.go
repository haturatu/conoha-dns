package conoha

import (
	"encoding/csv"
	"fmt"
	"io"
	"strings"
)

type manager struct {
	client      *Client
	domains     []Domain
	out, errOut io.Writer
}

func (m *manager) allDomains() ([]Domain, error) {
	if m.domains != nil {
		return m.domains, nil
	}
	var response struct {
		Domains []Domain `json:"domains"`
	}
	if err := m.client.request("GET", "/v1/domains", nil, &response); err != nil {
		return nil, err
	}
	m.domains = response.Domains
	return m.domains, nil
}
func (m *manager) domainID(identifier string) (string, error) {
	domains, err := m.allDomains()
	if err != nil {
		return "", err
	}
	if isShortID(identifier) {
		for _, domain := range domains {
			if shortID(domain.UUID) == identifier {
				return domain.UUID, nil
			}
		}
	}
	normalized := normalizeDomain(identifier)
	for _, domain := range domains {
		if domain.Name == normalized {
			return domain.UUID, nil
		}
	}
	return "", fmt.Errorf("ドメイン '%s' が見つかりませんでした。", identifier)
}
func (m *manager) domainName(id string) (string, error) {
	domains, err := m.allDomains()
	if err != nil {
		return "", err
	}
	for _, domain := range domains {
		if domain.UUID == id {
			return domain.Name, nil
		}
	}
	return "", fmt.Errorf("ドメインID '%s' が見つかりませんでした。", id)
}

func (m *manager) listDomains(csvOutput bool) error {
	domains, err := m.allDomains()
	if err != nil {
		return err
	}
	if csvOutput {
		fmt.Fprintln(m.errOut, "ドメイン一覧をCSV形式で出力します...")
		if len(domains) == 0 {
			fmt.Fprintln(m.errOut, "  (ドメインはありません)")
			return nil
		}
		writer := csv.NewWriter(m.out)
		defer writer.Flush()
		_ = writer.Write([]string{"ID", "Name"})
		for _, d := range domains {
			_ = writer.Write([]string{shortID(d.UUID), d.Name})
		}
		return writer.Error()
	}
	if len(domains) == 0 {
		_, err = fmt.Fprintln(m.out, "  (ドメインはありません)")
		return err
	}
	fmt.Fprintf(m.out, "  %-10s %-30s\n", "ID", "Name")
	for _, d := range domains {
		fmt.Fprintf(m.out, "  %-10s %-30s\n", shortID(d.UUID), d.Name)
	}
	return nil
}
func (m *manager) addDomain(name, email string) error {
	name = normalizeDomain(name)
	fmt.Fprintf(m.out, "ドメイン '%s' を追加しています...\n", name)
	var d Domain
	if err := m.client.request("POST", "/v1/domains", map[string]string{"name": name, "email": email}, &d); err != nil {
		return err
	}
	fmt.Fprintln(m.out, "ドメインが正常に追加されました。")
	_, err := fmt.Fprintf(m.out, "  ID: %s, Name: %s\n", d.UUID, d.Name)
	return err
}
func (m *manager) deleteDomain(identifier string) error {
	id, err := m.domainID(identifier)
	if err != nil {
		return err
	}
	name, err := m.domainName(id)
	if err != nil {
		return err
	}
	fmt.Fprintf(m.out, "ドメイン '%s' (ID: %s) を削除しています...\n", name, id)
	if err = m.client.request("DELETE", "/v1/domains/"+id, nil, nil); err != nil {
		return err
	}
	_, err = fmt.Fprintln(m.out, "ドメインが正常に削除されました。")
	return err
}

func (m *manager) records(id string) ([]Record, error) {
	var response struct {
		Records []Record `json:"records"`
	}
	err := m.client.request("GET", "/v1/domains/"+id+"/records", nil, &response)
	return response.Records, err
}
func (m *manager) listRecords(identifier string, csvOutput bool) error {
	id, err := m.domainID(identifier)
	if err != nil {
		return err
	}
	records, err := m.records(id)
	if err != nil {
		return err
	}
	if csvOutput {
		if len(records) == 0 {
			fmt.Fprintln(m.errOut, "  (レコードはありません)")
			return nil
		}
		w := csv.NewWriter(m.out)
		defer w.Flush()
		_ = w.Write([]string{"ID", "Name", "Type", "Data", "TTL"})
		for _, r := range records {
			_ = w.Write([]string{shortID(r.UUID), r.Name, r.Type, r.Data, formatTTL(r.TTL)})
		}
		return w.Error()
	}
	if len(records) == 0 {
		_, err = fmt.Fprintln(m.out, "  (レコードはありません)")
		return err
	}
	nameW, typeW := 4, 4
	for _, r := range records {
		if len(r.Name) > nameW {
			nameW = len(r.Name)
		}
		if len(r.Type) > typeW {
			typeW = len(r.Type)
		}
	}
	fmt.Fprintf(m.out, "  %-10s %-*s   %-*s   %-6s   %s\n", "ID", nameW, "Name", typeW, "Type", "TTL", "Data")
	for _, r := range records {
		fmt.Fprintf(m.out, "  %-10s %-*s   %-*s   %-6s   %s\n", shortID(r.UUID), nameW, r.Name, typeW, r.Type, formatTTL(r.TTL), r.Data)
	}
	return nil
}
func formatTTL(ttl *int) string {
	if ttl == nil {
		return "<nil>"
	}
	return fmt.Sprint(*ttl)
}

func (m *manager) addRecord(identifier, name, typ, data string, ttl int, priority, weight, port *int) error {
	id, err := m.domainID(identifier)
	if err != nil {
		return err
	}
	domain, err := m.domainName(id)
	if err != nil {
		return err
	}
	name = normalizeRecordName(domain, name)
	fmt.Fprintf(m.out, "ドメイン '%s' にレコード '%s' を追加しています...\n", domain, name)
	payload := map[string]any{"name": name, "type": typ, "data": data, "ttl": ttl}
	optional(payload, priority, weight, port)
	var record Record
	if err = m.client.request("POST", "/v1/domains/"+id+"/records", payload, &record); err != nil {
		return err
	}
	fmt.Fprintln(m.out, "レコードが正常に追加されました。")
	_, err = fmt.Fprintf(m.out, "  ID: %s, Name: %s, Type: %s, Data: %s\n", shortID(record.UUID), record.Name, record.Type, record.Data)
	return err
}
func optional(payload map[string]any, priority, weight, port *int) {
	if priority != nil {
		payload["priority"] = *priority
	}
	if weight != nil {
		payload["weight"] = *weight
	}
	if port != nil {
		payload["port"] = *port
	}
}
func (m *manager) deleteRecord(identifier, short string) error {
	id, err := m.domainID(identifier)
	if err != nil {
		return err
	}
	domain, err := m.domainName(id)
	if err != nil {
		return err
	}
	items, err := m.records(id)
	if err != nil {
		return err
	}
	full, err := findFullUUID(items, short)
	if err != nil {
		return err
	}
	fmt.Fprintf(m.out, "ドメイン '%s' からレコードID '%s' (UUID: %s) を削除しています...\n", domain, short, full)
	if err = m.client.request("DELETE", "/v1/domains/"+id+"/records/"+full, nil, nil); err != nil {
		return err
	}
	_, err = fmt.Fprintln(m.out, "レコードが正常に削除されました。")
	return err
}
func (m *manager) updateRecord(identifier, short string, o options) error {
	id, err := m.domainID(identifier)
	if err != nil {
		return err
	}
	domain, err := m.domainName(id)
	if err != nil {
		return err
	}
	items, err := m.records(id)
	if err != nil {
		return err
	}
	full, err := findFullUUID(items, short)
	if err != nil {
		return err
	}
	fmt.Fprintf(m.out, "レコードID '%s' (UUID: %s) の現在の情報を取得しています...\n", short, full)
	var current Record
	if err = m.client.request("GET", "/v1/domains/"+id+"/records/"+full, nil, &current); err != nil {
		return err
	}
	name := current.Name
	if o.newName != nil {
		name = *o.newName
	}
	payload := map[string]any{"name": normalizeRecordName(domain, name), "type": current.Type, "data": current.Data, "description": current.Description}
	if o.newType != nil {
		payload["type"] = *o.newType
	}
	if o.newData != nil {
		payload["data"] = *o.newData
	}
	ttl, priority, weight, port := current.TTL, current.Priority, current.Weight, current.Port
	if o.newTTL != nil {
		ttl = o.newTTL
	}
	if o.newPriority != nil {
		priority = o.newPriority
	}
	if o.newWeight != nil {
		weight = o.newWeight
	}
	if o.newPort != nil {
		port = o.newPort
	}
	if ttl != nil {
		payload["ttl"] = *ttl
	}
	if priority != nil {
		payload["priority"] = *priority
	}
	if weight != nil {
		payload["weight"] = *weight
	}
	if port != nil {
		payload["port"] = *port
	}
	fmt.Fprintf(m.out, "レコードID '%s' を更新しています...\n", short)
	var updated Record
	if err = m.client.request("PUT", "/v1/domains/"+id+"/records/"+full, payload, &updated); err != nil {
		return err
	}
	fmt.Fprintln(m.out, "レコードが正常に更新されました。")
	_, err = fmt.Fprintf(m.out, "  ID: %s, Name: %s, Type: %s, Data: %s, TTL: %s\n", shortID(updated.UUID), updated.Name, updated.Type, updated.Data, formatTTL(updated.TTL))
	return err
}

func normalizeDomain(value string) string {
	if strings.HasSuffix(value, ".") {
		return value
	}
	return value + "."
}
func normalizeRecordName(domain, name string) string {
	if name == "@" {
		return normalizeDomain(domain)
	}
	clean := strings.TrimSuffix(domain, ".")
	if !strings.HasSuffix(name, clean) {
		name += "." + clean
	}
	return normalizeDomain(name)
}
