These instructions apply to all quizzes that use Chipyard experiments. Everything remains the same up to the compilation step, where you need to compile the new architecture.

Make sure you have the updated repo version:

```
git pull
```

Start the Chipyard container:
```
docker compose run --rm chipyard
```

Load the Chipyard environment:
```
cd /workspace/chipyard
source env.sh
```
Compile the benchmark:
```
cd /workspace/course/benchmarks
make
```

Compile the configuration (current: ` BaselineConfig `, ` LargeL1Config `):
```
cd /workspace/chipyard/sims/verilator
make CONFIG=LargeL1Config
```

Run the provided ISP benchmark:

` quiz-run LargeL1Config isp` or the full path ` /workspace/course-scripts/quiz-run.sh LargeL1Config isp` should work with up-to-date repos. Note that BaselineConfig is the default configuration in the script, so if you don't specify a config, it will run the baseline.

This might take several minutes depending on your computer speed. The output should provide performance statistics for the different phases of isp_bench:  
gain  
vfilter  
downscale  
bgmodel  
detect  

Now, you are ready to answer thet quiz questions based on these stats.
