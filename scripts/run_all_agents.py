def main():
    from core.kernel import Kernel
    kernel = Kernel.from_config("config/test_agents.json")
    kernel.run(max_steps=5000, max_sim_seconds=10)
    kernel.shutdown()

if __name__ == "__main__":
    main()

