package conoha

import (
	"fmt"
	"strconv"

	"github.com/cespare/xxhash/v2"
)

func shortID(uuid string) string { return fmt.Sprintf("%016x", xxhash.Sum64String(uuid))[:8] }

func isShortID(value string) bool {
	if len(value) != 8 {
		return false
	}
	_, err := strconv.ParseUint(value, 16, 32)
	return err == nil
}

func findFullUUID(items []Record, id string) (string, error) {
	for _, item := range items {
		if shortID(item.UUID) == id {
			return item.UUID, nil
		}
	}
	return "", fmt.Errorf("指定されたID '%s' に一致するアイテムが見つかりませんでした。", id)
}
