package main

import (
	"fmt"
	"os"

	"conoha-dns/internal/conoha"
)

func main() {
	if err := conoha.Run(os.Args[1:], os.Stdout, os.Stderr); err != nil {
		if exit, ok := err.(conoha.ExitError); ok {
			os.Exit(exit.Code)
		}
		fmt.Fprintf(os.Stderr, "予期せぬエラーが発生しました: %v\n", err)
		os.Exit(1)
	}
}
