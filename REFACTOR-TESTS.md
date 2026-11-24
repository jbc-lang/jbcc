# Temporary jBC test sources

**238 of 561 collected tests** wrote at least one temporary `.b` file
during the full suite run. Each checkbox names one test method in
[tests/test_compiler.py](tests/test_compiler.py). A method can create or
rewrite several sources, including in subtests. This inventory covers
`.b` paths, so a test that only writes extensionless sources or includes
falls outside this list.

Check off a test after moving its fixed source to fixtures or confirming
that it needs to generate its source. Keep case-specific setup and
assertions in Python. Use numbered fixtures for fixed variants of one
case and descriptive names for separate behaviors or linked routines.

## Sequential files, printing and tape I/O (10)

- [x] `test_block_io_operand_diagnostics`
- [x] `test_timeout_diagnostics` — Keep generated variants that depend on a template or on case-specific bytes.
- [x] `test_seek_empty_operands`
- [x] `test_report_diagnostics`
- [x] `test_rewind_invalid_channel`
- [x] `test_readt_invalid_channel`
- [x] `test_writet_diagnostics`
- [x] `test_weof_invalid_channel`
- [x] `test_sequential_file_status`
- [x] `test_close_by_reference_retires_local_cleanup`

## Record files, locks and select lists (24)

- [x] `test_status_wrong_argument_count`
- [x] `test_status_empty_descriptor`
- [x] `test_delete_records`
- [x] `test_clearfile`
- [x] `test_clearfile_locked_dispatch_preserves_records`
- [x] `test_read_setting_uses_record_status_and_branch_order`
- [x] `test_read_setting_requires_destination_and_conditional_arm`
- [x] `test_readu_unhandled_fixture_conflict`
- [x] `test_recordlocku_reserves_key_and_reports_contention`
- [x] `test_recordlocku_unhandled_contention_reports_call_site`
- [x] `test_release_on_error_reports_invalid_files_and_preserves_foreign_locks`
- [x] `test_assign_system_resets_blocked_record_lock_counter`
- [x] `test_assign_system_diagnostics`
- [x] `test_readv`
- [x] `test_readvu_diagnostics`
- [x] `test_write_on_error_diagnostics`
- [x] `test_writeu_unhandled_failure`
- [x] `test_writev_field_number_diagnostics`
- [x] `test_inmat_requires_a_matrix_argument`
- [x] `test_matread`
- [x] `test_matwrite`
- [x] `test_file_select`
- [x] `test_sselect_diagnostics`
- [x] `test_clearselect`

## Routine calls, functions and linkage (22)

- [x] `test_callonexit_dispatches_linked_callbacks`
- [x] `test_bang_subroutine_names`
- [x] `test_call_aliases_and_expression_arguments`
- [x] `test_indirect_call`
- [x] `test_empty_actual_uses_local_storage_for_mat_formal`
- [x] `test_empty_mat_actual_requires_dimension_before_use`
- [x] `test_callc_subroutine_exists_checks_linked_subroutines`
- [x] `test_callc_subroutine_exists_requires_two_arguments`
- [x] `test_call_expands_equates_in_arguments_and_indirect_targets`
- [x] `test_quoted_and_punctuated_direct_routine_names`
- [x] `test_quoted_direct_target_preserves_whitespace_and_punctuation`
- [x] `test_indirect_call_diagnostics` — Keep generated variants that depend on a template or on case-specific bytes.
- [x] `test_indirect_call_through_matrix_element`
- [x] `test_indirect_matrix_call_uses_normal_matrix_diagnostics`
- [x] `test_multiline_call`
- [x] `test_deffun_call_as_statement_discards_return_and_updates_argument`
- [x] `test_function_arguments_and_returns`
- [x] `test_matrix_parameters`
- [x] `test_matrix_parameter_diagnostics`
- [x] `test_function_diagnostics`
- [x] `test_bad_routine_references`
- [x] `test_seqx_resolves_as_external_function`

## Compiler diagnostics and preprocessing (7)

- [x] `test_diagnostics_preserve_existing_output`
- [x] `test_period_label_diagnostics`
- [x] `test_comparison_signs_keep_reference_spacing_rules`
- [x] `test_lit_equates_expand_quoted_source`
- [x] `test_lit_equate_diagnostic_points_inside_definition`
- [x] `test_preprocessor_conditionals_and_include_guards`
- [x] `test_preprocessor_conditional_diagnostics`

## Control flow and variable assignment (24)

- [x] `test_stop_and_abort_from_main`
- [x] `test_stop_and_abort_from_routine`
- [x] `test_loop_exit_control_flow_diagnostics`
- [x] `test_increment_and_decrement_expression_values`
- [x] `test_increment_and_decrement_diagnostics`
- [x] `test_spaced_concatenating_assignment_requires_initial_value`
- [x] `test_compound_assignment_checks_conditionally_assigned_target`
- [x] `test_indexed_jump_selector`
- [x] `test_indexed_jump_range`
- [x] `test_jump_discards_step_when_reentering_a_completed_for`
- [x] `test_next_after_jump_requires_assigned_counter`
- [x] `test_return_to_unwinds_subroutine`
- [x] `test_return_to_without_caller`
- [x] `test_return_to_bypasses_for_header_with_explicit_step`
- [x] `test_deferred_scalar_read_warns_and_fails_only_when_reached`
- [x] `test_deferred_reads_still_reject_unknown_functions`
- [x] `test_assignment_predicates_on_arguments`
- [x] `test_expression_reads_after_conditional_assignment_are_checked_at_runtime`
- [x] `test_scalar_reads_after_case_are_checked_at_runtime`
- [x] `test_case_assignment_diagnostics_exclude_unreachable_and_sibling_arms`
- [x] `test_scalar_reads_after_for_are_checked_at_runtime`
- [x] `test_for_reads_check_values_from_earlier_iterations`
- [x] `test_for_reads_without_an_initializer_are_compile_errors`
- [x] `test_assignment_probe_does_not_initialize`

## Arithmetic and numeric builtins (27)

- [ ] `test_integer_limits`
- [ ] `test_invalid_precision`
- [ ] `test_dround_diagnostics`
- [ ] `test_smul_diagnostics`
- [ ] `test_sdiv_diagnostics`
- [ ] `test_adds_diagnostics`
- [ ] `test_infix_reuse_requires_scalar`
- [ ] `test_muls_diagnostics`
- [ ] `test_divs_substitutes_zero_for_zero_divisors`
- [ ] `test_infix_reuse_division_reports_invalid_operands`
- [ ] `test_divs_diagnostics`
- [ ] `test_subs_diagnostics`
- [ ] `test_ln_diagnostics`
- [ ] `test_exp_diagnostics`
- [ ] `test_sqrt_diagnostics`
- [ ] `test_power_domain_and_diagnostics`
- [ ] `test_randomize_wrong_argument_count`
- [ ] `test_rnd_invalid_bound`
- [ ] `test_bitxor_diagnostics`
- [ ] `test_mod_requires_numeric_operands`
- [ ] `test_neg_substitutes_zero`
- [ ] `test_negs_warns_for_nonnumeric_elements`
- [ ] `test_abs_diagnostics`
- [ ] `test_abss_diagnostics`
- [ ] `test_division_by_zero`
- [ ] `test_div_requires_nonzero_numeric_operands`
- [ ] `test_compound_division_by_zero`

## Strings, conversion, formatting and dynamic arrays (26)

- [ ] `test_locate_diagnostics`
- [ ] `test_iconv_diagnostics`
- [ ] `test_oconv_diagnostics`
- [ ] `test_str_repetition_diagnostics`
- [ ] `test_spaces_diagnostics`
- [ ] `test_left_right_require_numeric_length`
- [ ] `test_counts_requires_two_arguments`
- [ ] `test_col_positions_require_no_arguments`
- [ ] `test_delimited_bracket_assignment_diagnostics`
- [ ] `test_substrings_requires_numeric_bounds`
- [ ] `test_fold_invalid_width`
- [ ] `test_fmts_invalid_mask`
- [ ] `test_trim_diagnostics`
- [ ] `test_find_diagnostics`
- [ ] `test_swap_diagnostics`
- [ ] `test_ereplace_diagnostics`
- [ ] `test_change_diagnostics`
- [ ] `test_string_mutations_check_conditionally_assigned_targets`
- [ ] `test_implicit_format_reports_uninitialized_mask_at_read`
- [ ] `test_fmt_diagnostics`
- [ ] `test_index_diagnostics`
- [ ] `test_insert_locations`
- [ ] `test_remove_shared_cursor`
- [ ] `test_remove_expression_diagnostics`
- [ ] `test_remove_checks_conditionally_assigned_source`
- [ ] `test_matchfield_invalid_field`

## Matrices and COMMON storage (25)

- [ ] `test_matbuild_diagnostics`
- [ ] `test_matparse_diagnostics`
- [ ] `test_common_storage`
- [ ] `test_conflicting_common_declarations`
- [ ] `test_common_member_keeps_first_slot_when_dimensioned_later`
- [ ] `test_repeated_include_reuses_common_matrix_slots`
- [ ] `test_repeated_common_matrix_rejects_incompatible_dimensions`
- [ ] `test_dim_reuses_named_and_unnamed_common_matrix_slots`
- [ ] `test_dim_rejects_a_common_matrix_rank_change`
- [ ] `test_common_matrix_subscript_mismatches_report_when_reached`
- [ ] `test_dim_reports_a_reached_common_matrix_resize`
- [ ] `test_runtime_common_dimensions`
- [ ] `test_local_dimensions_per_invocation`
- [ ] `test_forward_matrix_declarations_follow_execution_order`
- [ ] `test_scalar_can_be_used_before_a_later_local_dim`
- [ ] `test_forward_matrix_errors_use_reference_location`
- [ ] `test_repeated_local_dim_reuses_storage_from_either_path`
- [ ] `test_repeated_local_dim_rejects_changed_rank`
- [ ] `test_repeated_local_dim_reports_reached_resize`
- [ ] `test_local_dimension_errors`
- [ ] `test_runtime_common_dimension_errors`
- [ ] `test_common_runtime_shape_across_routines`
- [ ] `test_matrix_assignment_diagnostics`
- [ ] `test_matrix_fill_evaluates_expression_once`
- [ ] `test_matrix_element_argument_and_bounds`

## Source encoding and byte-oriented builtins (13)

- [ ] `test_cipher_diagnostics`
- [ ] `test_hexadecimal_conversion_diagnostics`
- [ ] `test_source_encoding_preserves_legacy_and_utf8_literal_bytes`
- [ ] `test_source_nul_is_ignored_in_comments`
- [ ] `test_source_nul_reports_its_location_in_active_text`
- [ ] `test_default_source_encoding_reports_invalid_utf8_in_an_include`
- [ ] `test_ascii_and_ebcdic_argument_counts`
- [ ] `test_utf8_and_latin1_round_trip_all_nonzero_bytes`
- [ ] `test_latin1_rejects_malformed_and_unrepresentable_utf8`
- [ ] `test_seq_reads_block_bytes`
- [ ] `test_seq_wrong_argument_count`
- [ ] `test_char_byte_range_diagnostics`
- [ ] `test_checksum_argument_diagnostics`

## External services and backend diagnostics (7)

- [ ] `test_jbasecoredump_requires_an_application_snapshot_backend`
- [ ] `test_xml_transforms_require_a_backend_when_reached`
- [ ] `test_xml_transform_argument_diagnostics`
- [ ] `test_indices_requires_backend_only_when_a_query_is_reached`
- [ ] `test_transactions_report_missing_backend_at_the_call`
- [ ] `test_defc_declarations_and_runtime_diagnostics`
- [ ] `test_defc_rejects_invalid_types_and_argument_counts`

## Corpus scanning and reporting (3)

- [ ] `test_corpus_reports_deferred_reads_in_includes`
- [ ] `test_corpus_can_summarize_next_name_mismatch_warnings`
- [ ] `test_corpus_report_can_preserve_source_bytes`

## Command execution and piped output (7)

- [ ] `test_capture_from_pipe`
- [ ] `test_exec_rejects_duplicate_returning_clause`
- [ ] `test_execute_large_stdout_and_stderr`
- [ ] `test_execute_result_diagnostics`
- [ ] `test_execute_rtnlist_requires_backend_before_running_command`
- [ ] `test_execute_child_program`
- [ ] `test_execute_command_diagnostics`

## Arguments and invocation strings (7)

- [ ] `test_invocation_sentence`
- [ ] `test_command_system_variable_uses_the_invocation_in_a_subroutine`
- [ ] `test_sentence_function_reads_invocation_in_a_subroutine`
- [ ] `test_sentence_function_preserves_get_argument_cursor`
- [ ] `test_sentence_function_diagnostics`
- [ ] `test_get_argument_preserves_argv_and_shares_cursor_across_routines`
- [ ] `test_get_argument_failures_and_diagnostics`

## Terminal input, echo and polling (18)

- [ ] `test_cursor_coordinate_diagnostics`
- [ ] `test_inputclear_discards_only_terminal_typeahead`
- [ ] `test_input_underscore_discards_excess_in_queue_and_pipe`
- [ ] `test_input_underscore_rings_bell_and_waits_for_enter`
- [ ] `test_keyin_shares_queued_and_piped_input`
- [ ] `test_keyin_reads_unedited_terminal_byte_and_restores_mode`
- [ ] `test_keyin_function_diagnostics`
- [ ] `test_timed_input_diagnostics`
- [ ] `test_input_negative_one_polls_without_consuming_bytes`
- [ ] `test_input_negative_one_polls_an_empty_open_pipe`
- [ ] `test_input_negative_one_detects_terminal_typeahead`
- [ ] `test_input_length_diagnostics`
- [ ] `test_hush_nonnumeric_operand`
- [ ] `test_break_key_controls_terminal_interrupts`
- [ ] `test_echo_controls_terminal_input_and_system24`
- [ ] `test_hush_terminal_input_and_printer`
- [ ] `test_input_terminal_echo`
- [ ] `test_system14_input_queue`

## Session identity and environment (13)

- [ ] `test_account_path_uses_working_directory`
- [ ] `test_terminal_type_aliases_follow_term`
- [ ] `test_tty_name_with_terminal_and_redirected_input`
- [ ] `test_port_number_aliases_use_startup_environment`
- [ ] `test_pid_uses_native_process_id_with_port_override`
- [ ] `test_user_root_is_shared_with_linked_routines_and_userstats`
- [ ] `test_user_root_limit_counts_bytes`
- [ ] `test_port_number_defaults_to_process_id`
- [ ] `test_invalid_port_number_reports_call_site`
- [ ] `test_who_uses_startup_login_name`
- [ ] `test_who_defaults_to_posix_user_name`
- [ ] `test_account_aliases_use_startup_account_name`
- [ ] `test_account_defaults_to_posix_user_name`

## User statistics (5)

- [ ] `test_userstats_native_snapshot_and_record_writes`
- [ ] `test_userstats_open_and_read_counters`
- [ ] `test_userstats_delete_and_clearfile_counters`
- [ ] `test_userstats_execute_and_input_counters`
- [ ] `test_userstats_reports_invalid_port_at_reference`
