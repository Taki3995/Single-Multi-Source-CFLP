option solver gurobi;
#option solver ipopt;
#option solver bonmin;
#options bonmin_options "bonmin.algorithm=B-BB bonmin.bb_log_interval=6 print_level=4 linear_solver=ma57"; 
#option snopt_options 'wantsol=8 outlev=2';
option gurobi_options 'outlev=1 mipgap 0.01 bestbound 1 logfile "./logfile.txt"'; 

param cli;
param loc;
param ICap{1 .. loc};
param FC{1 .. loc};
param dem{1 .. cli};
param TC{1 .. cli, 1 .. loc};

var x {1 .. loc} integer >=0 <=1;
var y {1 .. cli, 1 .. loc} integer >=0 <=1;

minimize Total_Cost: ((sum {j in 1..loc} x[j] * FC[j])) + ((sum {j in 1..loc} (sum {i in 1..cli} y[i,j] * TC[i,j]))) ;

s.t.			 
						
	allocation1 {i in 1..cli}:    	sum {j in 1..loc} y[i,j] = 1;

	capacity {j in 1..loc}: sum {i in 1..cli} dem[i]*y[i,j] <= ICap[j]*x[j];
	
