if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Hello World')
    parser.add_argument('--nodes', dest='nodes', metavar='Node', nargs='+', required=True)
    args = parser.parse_args()
    print(args.nodes)