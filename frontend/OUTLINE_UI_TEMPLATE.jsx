{/* Generate Outline Button - Add after contextPanel */ }
{
    contextPanel[index] && (
        <div className="text-center my-4">
            <button
                onClick={() => handleGenerateOutline(index, prompt.prompt)}
                disabled={loadingOutline[index]}
                className="px-5 py-2.5 bg-gradient-to-r from-purple-600 to-purple-700 text-white text-sm rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition-all flex items-center gap-2 shadow-sm mx-auto"
            >
                {loadingOutline[index] ? (
                    <>
                        <ArrowPathIcon className="w-4 h-4 animate-spin" />
                        Generating Outline...
                    </>
                ) : (
                    '📝 Generate Essay Outline'
                )}
            </button>
        </div>
    )
}

{/* Essay Outline Display - Collapsible */ }
{
    outline[index] && (
        <div className="bg-white rounded-xl border-2 border-purple-200 shadow-sm overflow-hidden mb-4">
            <button
                onClick={() => setOutlineExpanded(prev => ({ ...prev, [index]: !prev[index] }))}
                className="w-full p-4 flex items-center justify-between text-left hover:bg-purple-50 transition-colors"
            >
                <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-purple-100 rounded-lg flex items-center justify-center">
                        <span className="text-lg">📝</span>
                    </div>
                    <h4 className="font-semibold text-purple-900">Essay Outline</h4>
                </div>
                {outlineExpanded[index] ? (
                    <ChevronUpIcon className="w-5 h-5 text-purple-600" />
                ) : (
                    <ChevronDownIcon className="w-5 h-5 text-purple-600" />
                )}
            </button>

            {outlineExpanded[index] && (
                <div className="p-5 bg-purple-50 border-t border-purple-200">
                    <div className="space-y-4">
                        {outline[index].outline?.map((section, i) => (
                            <div key={i} className="bg-white rounded-lg border-l-4 border-purple-400 p-4 shadow-sm">
                                <h5 className="font-bold text-purple-800 mb-2">
                                    {section.section}
                                    <span className="text-sm font-normal text-purple-600 ml-2">
                                        ({section.word_count})
                                    </span>
                                </h5>
                                <ul className="mt-2 space-y-2">
                                    {section.points?.map((point, j) => (
                                        <li key={j} className="text-sm text-gray-700 flex items-start gap-2">
                                            <span className="text-purple-500 mt-0.5">•</span>
                                            <span>{point}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        ))}

                        {/* Total Word Count */}
                        <div className="bg-purple-100 rounded-lg p-3">
                            <p className="text-sm font-semibold text-purple-900">
                                📏 Total: {outline[index].total_word_count}
                            </p>
                        </div>

                        {/* Writing Tips */}
                        {outline[index].writing_tips && outline[index].writing_tips.length > 0 && (
                            <div className="bg-white rounded-lg border border-purple-200 p-4">
                                <h6 className="text-sm font-bold text-purple-800 mb-2 flex items-center gap-2">
                                    <span>💡</span> Writing Tips
                                </h6>
                                <ul className="space-y-1.5">
                                    {outline[index].writing_tips.map((tip, i) => (
                                        <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                                            <span className="text-purple-500 font-bold">{i + 1}.</span>
                                            <span>{tip}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        )}
                    </div>

                    <p className="text-xs text-purple-600 mt-4 text-center italic">
                        ↓ Use this outline as a guide while writing your essay below
                    </p>
                </div>
            )}
        </div>
    )
}
