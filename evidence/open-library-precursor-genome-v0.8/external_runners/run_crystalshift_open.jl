using CrystalShift
using LinearAlgebra
using Statistics

const K_EXPAND = 3
const STD_NOISE = 0.01
const MEAN_THETA = [1.0, 0.5, 0.5]
const STD_THETA = [0.1, 0.05, 0.1]
const NORMALIZATION_CONSTANT = 2.5

function option(args, name, default=nothing; required=false)
    prefix = name * "="
    for arg in args
        if startswith(arg, prefix)
            return split(arg, "="; limit=2)[2]
        end
    end
    required && error("missing required option: " * name)
    return default
end

function read_csv_rows(path)
    lines = readlines(path)
    isempty(lines) && error("empty CSV: " * path)
    header = split(strip(lines[1]), ',')
    rows = Vector{Dict{String,String}}()
    for line in lines[2:end]
        isempty(strip(line)) && continue
        values = split(strip(line), ',')
        length(values) == length(header) ||
            error("wrong field count in " * path)
        push!(rows, Dict(header[i] => String(values[i]) for i in eachindex(header)))
    end
    return rows
end

function read_candidate_blocks(path)
    blocks = Vector{Vector{String}}()
    current = String[]
    for line in eachline(path)
        if strip(line) == "#"
            isempty(current) || push!(blocks, copy(current))
            empty!(current)
        else
            push!(current, String(line))
        end
    end
    isempty(current) || push!(blocks, copy(current))
    return blocks
end

function load_selected_candidates(path, all_ids, selected_ids)
    blocks = read_candidate_blocks(path)
    length(blocks) == length(all_ids) ||
        error("candidate table and stick blocks disagree")
    wanted = Set(selected_ids)
    phases = CrystalPhase[]
    for (block, phase_id) in zip(blocks, all_ids)
        phase_id in wanted || continue
        fields = split(block[1], ',')
        fields[1] = string(length(phases))
        block[1] = join(fields, ',')
        push!(phases, CrystalPhase(join(block, "\n"), 0.1, CrystalShift.Gauss()))
    end
    length(phases) == length(selected_ids) ||
        error("selected candidate mismatch")
    return phases
end

function load_spectrum(path, wavelength_angstrom)
    x = Float64[]
    y = Float64[]
    for line in eachline(path)
        values = split(strip(line))
        isempty(values) && continue
        length(values) >= 2 || error("bad spectrum row in " * path)
        push!(x, parse(Float64, values[1]))
        push!(y, parse(Float64, values[2]))
    end
    q = 4pi .* sin.(deg2rad.(x ./ 2.0)) ./ (wavelength_angstrom / 10.0)
    order = sortperm(q)
    q = q[order]
    y = y[order]
    keep = isfinite.(q) .& isfinite.(y)
    q = q[keep]
    y = y[keep]
    length(q) >= 100 || error("too few valid points in " * path)
    sorted_y = sort(copy(y))
    baseline = sorted_y[max(1, ceil(Int, 0.01 * length(sorted_y)))]
    y = max.(y .- baseline, 0.0)
    ymax = maximum(y)
    ymax > 0.0 || error("zero normalized spectrum in " * path)
    y ./= ymax
    return q, y
end

function node_phases(node)
    return sort(unique([phase.id + 1 for phase in node.phase_model.CPs]))
end

function run_query(path, phases, wavelength_angstrom, max_depth)
    x, y = load_spectrum(path, wavelength_angstrom)
    first_peak = minimum(minimum(peak.q for peak in phase.peaks) for phase in phases)
    last_peak = maximum(maximum(peak.q for peak in phase.peaks) for phase in phases)
    keep = (x .>= first_peak) .& (x .<= last_peak)
    x = x[keep]
    y = y[keep]
    length(x) >= 100 || error("too few common q points in " * path)
    tree = Lazytree(phases, x)
    results = search!(
        tree,
        x,
        y,
        max_depth,
        K_EXPAND,
        false,
        false,
        8.0,
        STD_NOISE,
        MEAN_THETA,
        STD_THETA;
        method=LM,
        maxiter=32,
        regularization=true,
        optimize_mode=Simple,
        em_loop_num=1,
    )
    nodes = reduce(vcat, results[2:end])
    probabilities = get_probabilities(
        nodes,
        x,
        y,
        MEAN_THETA,
        STD_THETA;
        renormalize=true,
        normalization_constant=NORMALIZATION_CONSTANT,
    )
    inclusion = zeros(Float64, length(phases))
    for index in eachindex(nodes)
        for phase_index in node_phases(nodes[index])
            inclusion[phase_index] += probabilities[index]
        end
    end
    order = sortperm(eachindex(inclusion), by=i -> (-inclusion[i], i))
    ranks = zeros(Int, length(inclusion))
    for (rank, phase_index) in enumerate(order)
        ranks[phase_index] = rank
    end
    best_index = argmax(probabilities)
    variance = sum(abs2, y .- mean(y))
    residual_fraction = sum(abs2, nodes[best_index].residual) / variance
    probability_order = sortperm(probabilities, rev=true)
    return inclusion, ranks, nodes, probabilities, probability_order, residual_fraction
end

function main()
    args = ARGS
    sticks = option(args, "--sticks", required=true)
    queries_path = option(args, "--queries", required=true)
    spectra_dir = option(args, "--spectra-dir", required=true)
    candidates_path = option(args, "--candidates", required=true)
    candidate_ids_arg = option(args, "--candidate-ids", required=true)
    predictions_out = option(args, "--out", required=true)
    sets_out = option(args, "--sets", required=true)
    unknown_out = option(args, "--unknown-out", required=true)
    max_depth = parse(Int, option(args, "--max-depth", "3"))
    max_queries = parse(Int, option(args, "--max-queries", string(typemax(Int))))

    selected_ids = String.(split(candidate_ids_arg, ","))
    query_rows = read_csv_rows(queries_path)
    candidate_rows = read_csv_rows(candidates_path)
    all_ids = [row["phase_id"] for row in candidate_rows]
    phases = load_selected_candidates(sticks, all_ids, selected_ids)

    open(predictions_out, "w") do handle
        println(handle, "query_id,phase_id,score,rank")
    end
    open(sets_out, "w") do handle
        println(handle, "query_id,set,probability")
    end
    open(unknown_out, "w") do handle
        println(handle, "query_id,unknown_score,best_probability")
    end

    for (query_number, row) in enumerate(query_rows)
        query_number > max_queries && break
        query_id = row["query_id"]
        wavelength = parse(Float64, row["wavelength_angstrom"])
        spectrum_path = joinpath(spectra_dir, basename(row["spectrum_file"]))
        inclusion, ranks, nodes, probabilities, probability_order, residual =
            run_query(spectrum_path, phases, wavelength, max_depth)
        open(predictions_out, "a") do handle
            for index in eachindex(inclusion)
                println(
                    handle,
                    join(
                        (
                            query_id,
                            selected_ids[index],
                            string(inclusion[index]),
                            string(ranks[index]),
                        ),
                        ",",
                    ),
                )
            end
        end
        open(sets_out, "a") do handle
            for index in probability_order[1:min(10, length(probability_order))]
                members = node_phases(nodes[index])
                println(
                    handle,
                    join(
                        (
                            query_id,
                            join(selected_ids[members], "|"),
                            string(probabilities[index]),
                        ),
                        ",",
                    ),
                )
            end
        end
        open(unknown_out, "a") do handle
            println(
                handle,
                join(
                    (query_id, string(residual), string(maximum(probabilities))),
                    ",",
                ),
            )
        end
        println("CRYSTALSHIFT_QUERY_PASS query_id=", query_id)
    end
    println("CRYSTALSHIFT_RUN_PASS")
end

main()
