using Cimt.RequirementDemo;

// This demo writes synthetic results. It never connects to devices or OpenAI.
var example = Path.GetFullPath(args.Length == 0 ? "examples/requirement-mapping" : args[0]);
return await MappingDemo.Run(example);
