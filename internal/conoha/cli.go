package conoha

import (
	"fmt"
	"io"
	"strconv"
	"strings"
)

// ExitError is an intentional process exit status.
type ExitError struct{ Code int }

func (e ExitError) Error() string { return fmt.Sprintf("exit status %d", e.Code) }

type options struct {
	action, listDomain                                              string
	addDomain, addRecord, updateRecord, deleteRecord                []string
	deleteDomain, output                                            string
	ttl                                                             int
	priority, weight, port, newTTL, newPriority, newWeight, newPort *int
	newName, newType, newData                                       *string
}

func Run(args []string, out, errOut io.Writer) error {
	o, err := parse(args, out, errOut)
	if err != nil {
		return err
	}
	if o.action == "help" {
		printHelp(out)
		return nil
	}
	c, err := newClient(o.action == "renew", out, errOut)
	if err != nil {
		if _, ok := err.(apiError); ok {
			fmt.Fprintln(errOut, "エラー: 要求に失敗しました。")
			fmt.Fprintln(errOut, err)
			return ExitError{4}
		}
		fmt.Fprintf(errOut, "エラー: %v\n", err)
		return ExitError{3}
	}
	if o.action == "renew" {
		fmt.Fprintln(out, "APIトークンが正常に更新されました。")
		return nil
	}
	if o.action == "auth" {
		fmt.Fprintln(out, "認証に成功し、APIトークンが利用可能です。")
		return nil
	}
	m := &manager{client: c, out: out, errOut: errOut}
	var opErr error
	switch o.action {
	case "list":
		if o.listDomain == "" {
			opErr = m.listDomains(o.output == "csv")
		} else {
			opErr = m.listRecords(o.listDomain, o.output == "csv")
		}
	case "add-domain":
		opErr = m.addDomain(o.addDomain[0], o.addDomain[1])
	case "delete-domain":
		opErr = m.deleteDomain(o.deleteDomain)
	case "add-record":
		opErr = m.addRecord(o.addRecord[0], o.addRecord[1], o.addRecord[2], o.addRecord[3], o.ttl, o.priority, o.weight, o.port)
	case "update-record":
		opErr = m.updateRecord(o.updateRecord[0], o.updateRecord[1], o)
	case "delete-record":
		opErr = m.deleteRecord(o.deleteRecord[0], o.deleteRecord[1])
	}
	if opErr == nil {
		return nil
	}
	if _, ok := opErr.(apiError); ok {
		fmt.Fprintln(errOut, "エラー: 要求に失敗しました。")
		fmt.Fprintln(errOut, opErr)
		return ExitError{4}
	}
	fmt.Fprintf(errOut, "エラー: %v\n", opErr)
	return nil
}

func parse(args []string, out, errOut io.Writer) (options, error) {
	o := options{ttl: 300}
	usage := func(message string) (options, error) {
		printUsage(errOut)
		fmt.Fprintf(errOut, "main.go: error: %s\n", message)
		return o, ExitError{2}
	}
	setAction := func(action string) error {
		if o.action != "" && o.action != "help" {
			_, e := usage("argument " + action + ": not allowed with another action")
			return e
		}
		o.action = action
		return nil
	}
	value := func(i *int, name string) (string, error) {
		*i++
		if *i >= len(args) {
			return "", ExitError{2}
		}
		return args[*i], nil
	}
	integer := func(i *int, name string, target **int) error {
		raw, err := value(i, name)
		if err != nil {
			return err
		}
		n, err := strconv.Atoi(raw)
		if err != nil {
			return ExitError{2}
		}
		*target = &n
		return nil
	}
	stringOption := func(i *int, name string, target **string) error {
		raw, err := value(i, name)
		if err == nil {
			*target = &raw
		}
		return err
	}
	for i := 0; i < len(args); i++ {
		a := args[i]
		switch a {
		case "-h", "--help":
			o.action = "help"
		case "--auth", "--renew":
			if err := setAction(strings.TrimPrefix(a, "--")); err != nil {
				return o, err
			}
		case "-l", "--list":
			if err := setAction("list"); err != nil {
				return o, err
			}
			if i+1 < len(args) && !strings.HasPrefix(args[i+1], "-") {
				i++
				o.listDomain = args[i]
			}
		case "-ad", "--add-domain":
			if err := setAction("add-domain"); err != nil {
				return o, err
			}
			for n := 0; n < 2; n++ {
				v, e := value(&i, a)
				if e != nil {
					return usage("argument " + a + ": expected 2 arguments")
				}
				o.addDomain = append(o.addDomain, v)
			}
		case "-dd", "--delete-domain":
			if err := setAction("delete-domain"); err != nil {
				return o, err
			}
			v, e := value(&i, a)
			if e != nil {
				return usage("argument " + a + ": expected one argument")
			}
			o.deleteDomain = v
		case "-ar", "--add-record":
			if err := setAction("add-record"); err != nil {
				return o, err
			}
			for n := 0; n < 4; n++ {
				v, e := value(&i, a)
				if e != nil {
					return usage("argument " + a + ": expected 4 arguments")
				}
				o.addRecord = append(o.addRecord, v)
			}
		case "-ur", "--update-record":
			if err := setAction("update-record"); err != nil {
				return o, err
			}
			for n := 0; n < 2; n++ {
				v, e := value(&i, a)
				if e != nil {
					return usage("argument " + a + ": expected 2 arguments")
				}
				o.updateRecord = append(o.updateRecord, v)
			}
		case "-dr", "--delete-record":
			if err := setAction("delete-record"); err != nil {
				return o, err
			}
			for n := 0; n < 2; n++ {
				v, e := value(&i, a)
				if e != nil {
					return usage("argument " + a + ": expected 2 arguments")
				}
				o.deleteRecord = append(o.deleteRecord, v)
			}
		case "-t", "--ttl":
			var p *int
			if e := integer(&i, a, &p); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
			o.ttl = *p
		case "-o", "--output":
			v, e := value(&i, a)
			if e != nil {
				return usage("argument " + a + ": expected one argument")
			}
			if v != "csv" {
				return usage("argument " + a + ": invalid choice: '" + v + "' (choose from 'csv')")
			}
			o.output = v
		case "--priority":
			if e := integer(&i, a, &o.priority); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
		case "--weight":
			if e := integer(&i, a, &o.weight); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
		case "--port":
			if e := integer(&i, a, &o.port); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
		case "--new-name":
			if e := stringOption(&i, a, &o.newName); e != nil {
				return usage("argument " + a + ": expected one argument")
			}
		case "--new-type":
			if e := stringOption(&i, a, &o.newType); e != nil {
				return usage("argument " + a + ": expected one argument")
			}
		case "--new-data":
			if e := stringOption(&i, a, &o.newData); e != nil {
				return usage("argument " + a + ": expected one argument")
			}
		case "--new-ttl":
			if e := integer(&i, a, &o.newTTL); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
		case "--new-priority":
			if e := integer(&i, a, &o.newPriority); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
		case "--new-weight":
			if e := integer(&i, a, &o.newWeight); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
		case "--new-port":
			if e := integer(&i, a, &o.newPort); e != nil {
				return usage("argument " + a + ": invalid int value")
			}
		default:
			return usage("unrecognized arguments: " + a)
		}
	}
	if o.action == "" {
		return usage("one of the arguments --auth --renew -l/--list -ad/--add-domain -dd/--delete-domain -ar/--add-record -ur/--update-record -dr/--delete-record is required")
	}
	if o.action == "add-record" {
		if err := validateRecord(o.addRecord[2], o.priority, o.weight, o.port, out, errOut); err != nil {
			return o, err
		}
	}
	if o.action == "update-record" {
		if o.newName == nil && o.newType == nil && o.newData == nil && o.newTTL == nil && o.newPriority == nil && o.newWeight == nil && o.newPort == nil {
			return usage("--update-recordには、--new-name, --new-type, --new-data, --new-ttl, --new-priority, --new-weight, --new-port のいずれか1つ以上の指定が必要です。")
		}
		if o.newType != nil {
			if err := validateRecord(*o.newType, o.newPriority, o.newWeight, o.newPort, out, errOut); err != nil {
				return o, err
			}
		}
	}
	return o, nil
}

func validateRecord(typ string, priority, weight, port *int, out, errOut io.Writer) error {
	missing := []string{}
	switch strings.ToUpper(typ) {
	case "MX":
		if priority == nil {
			missing = []string{"--priority"}
		}
	case "SRV":
		if priority == nil {
			missing = append(missing, "--priority")
		}
		if weight == nil {
			missing = append(missing, "--weight")
		}
		if port == nil {
			missing = append(missing, "--port")
		}
	}
	if len(missing) > 0 {
		printUsage(errOut)
		fmt.Fprintf(errOut, "main.go: error: %sレコードには %s の指定が必要です。\n", strings.ToUpper(typ), strings.Join(missing, ", "))
		return ExitError{2}
	}
	return nil
}

func printUsage(w io.Writer) {
	fmt.Fprint(w, `usage: conoha-dns [-h]
                  (--auth | --renew | -l [DOMAIN] | -ad NAME EMAIL | -dd DOMAIN | -ar DOMAIN NAME TYPE DATA | -ur DOMAIN RECORD_ID | -dr DOMAIN RECORD_ID)
                  [-t TTL] [-o {csv}] [--new-name NEW_NAME] [--new-type NEW_TYPE]
                  [--priority PRIORITY] [--weight WEIGHT] [--port PORT]
                  [--new-data NEW_DATA] [--new-ttl NEW_TTL] [--new-priority NEW_PRIORITY]
                  [--new-weight NEW_WEIGHT] [--new-port NEW_PORT]
`)
}
func printHelp(w io.Writer) {
	printUsage(w)
	fmt.Fprint(w, `
ConoHa DNS API (v1) を操作するCLIツール

options:
  -h, --help            show this help message and exit
  --auth                APIトークンを認証・取得する
  --renew               APIトークンを強制的に再認証・更新する
  -l [DOMAIN], --list [DOMAIN]
                        ドメイン一覧または指定ドメインのレコード一覧表示
  -ad NAME EMAIL, --add-domain NAME EMAIL
                        ドメイン追加
  -dd DOMAIN, --delete-domain DOMAIN
                        ドメインを名前またはIDで削除
  -ar DOMAIN NAME TYPE DATA, --add-record DOMAIN NAME TYPE DATA
                        レコード追加
  -ur DOMAIN RECORD_ID, --update-record DOMAIN RECORD_ID
                        レコード更新
  -dr DOMAIN RECORD_ID, --delete-record DOMAIN RECORD_ID
                        レコード削除
  -t TTL, --ttl TTL     レコード追加時のTTL(秒)。デフォルト: 300
  -o {csv}, --output {csv}
                        出力形式をCSVにします。'-l'での一覧表示時のみ有効です。
  --priority PRIORITY   MX/SRVレコード追加時の優先度
  --weight WEIGHT       SRVレコード追加時の重み
  --port PORT           SRVレコード追加時のポート番号
  --new-name NEW_NAME   更新後のレコード名
  --new-type NEW_TYPE   更新後のレコードタイプ
  --new-data NEW_DATA   更新後のレコードデータ
  --new-ttl NEW_TTL     更新後のTTL
  --new-priority NEW_PRIORITY
                        更新後の優先度
  --new-weight NEW_WEIGHT
                        更新後の重み
  --new-port NEW_PORT   更新後のポート番号

使用例:
  # APIトークンを認証・取得
  conoha-dns --auth

  # APIトークンを強制的に再認証・更新
  conoha-dns --renew

  # ドメイン一覧表示
  conoha-dns -l

  # レコード一覧をCSV形式で標準出力
  conoha-dns -l example.com --output csv > records.csv

  # Aレコード追加 (サブドメインtestを補完してtest.example.comを追加)
  conoha-dns -ar example.com @ A 192.0.2.1
  conoha-dns -ar example.com test A 192.0.2.1
  conoha-dns -ar example.com mail MX mail.example.net. --priority 10
  conoha-dns -ar example.com _sip._tcp SRV sip.example.net. --priority 10 --weight 20 --port 5060

  # レコード更新 (レコードIDを指定し、新しいIPアドレスを設定)
  conoha-dns -ur example.com <record_id> --new-data 192.0.2.2

  # レコード削除 (レコードIDは -l example.com で確認)
  conoha-dns -dr example.com <record_id>
`)
}
