import argparse
import sys
import json
from src.memory.core import remember, recall

def main():
    parser = argparse.ArgumentParser(description="Kanon Long-term Memory CLI Interface")
    subparsers = parser.add_subparsers(dest="command", help="Memory commands")
    
    # remember コマンドの定義
    remember_parser = subparsers.add_parser("remember", help="Save a memory topic")
    remember_parser.add_argument("--topic", required=True, help="Topic of the memory")
    remember_parser.add_argument("--content", required=True, help="Detailed content of the memory")
    remember_parser.add_argument("--level", default="L1", choices=["L1", "L3", "L4"], help="Memory level (default: L1)")
    remember_parser.add_argument("--category", default="general", help="ADC Category code")
    remember_parser.add_argument("--tags", default="", help="Comma separated tags")
    
    # recall コマンドの定義
    recall_parser = subparsers.add_parser("recall", help="Search and retrieve a memory")
    recall_parser.add_argument("--query", required=True, help="Search query string")
    recall_parser.add_argument("--level", choices=["L1", "L3", "L4"], help="Filter by specific level")
    
    args = parser.parse_args()
    
    if args.command == "remember":
        tags_list = [tag.strip() for tag in args.tags.split(",") if tag.strip()]
        success = remember(
            topic=args.topic,
            content=args.content,
            level=args.level,
            category=args.category,
            tags=tags_list
        )
        if success:
            print(json.dumps({"status": "success", "message": f"Successfully remembered topic '{args.topic}' at level {args.level}."}))
            sys.exit(0)
        else:
            print(json.dumps({"status": "error", "message": "Failed to save memory."}))
            sys.exit(1)
            
    elif args.command == "recall":
        res = recall(query=args.query, level=args.level)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        if res.get("status") == "success":
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()
